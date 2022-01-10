"""The client logic of anyd framework to talk with vpnm daemon.
Also contains some network-related actions and file storage
management."""
from __future__ import annotations

import ipaddress
import re
import socket
import subprocess
from typing import Tuple

from anyd import ClientSession

from vpnm import systemd, web_api
from vpnm.utils import JSONFileStorage, get_actual_address


def _get_ifindex_and_ifaddr(ifindex: int | None, ifaddr: str | None) -> Tuple:
    private_networks = [
        "10.0.0.0/8",
        "100.64.0.0/10",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "198.18.0.0/15",
    ]
    proc = subprocess.run(["ip", "a"], check=True, capture_output=True)

    if ifindex and ifaddr and ifindex and ifaddr in proc.stdout.decode():
        return (ifindex, ifaddr)

    pattern = re.compile(r"tun\d*")
    ifaces = pattern.findall(proc.stdout.decode())

    if not ifaces:
        ifindex = 0
    else:
        pattern = re.compile(r"\d*")
        indicies = [i for i in pattern.findall("".join(ifaces)) if i.isnumeric()]
        ifindex = max(list(map(int, indicies))) + 1

    pattern = re.compile(r"\d*.\d*.\d*.\d*/\d*")
    nets = pattern.findall(proc.stdout.decode())

    for network in private_networks:
        for subnet in ipaddress.IPv4Network(network).subnets():
            if subnet.exploded not in nets:
                ifaddr = f"{subnet[2].exploded}/24"
    return (ifindex, ifaddr)


def _get_default_gateway_with_metric(ifindex: str) -> Tuple:
    proc = subprocess.run(["ip", "route"], check=True, capture_output=True)
    pattern = re.compile(r"default")
    defaults = [
        record
        for record in proc.stdout.decode().split("\n")
        if f"tun{ifindex}" not in record and pattern.match(record)
    ]
    pattern = re.compile(r"metric \d*")
    metrics = pattern.findall("".join(defaults))
    pattern = re.compile(r"via \d*.\d*.\d*.\d*")
    if metrics:
        metric = min(
            [int(metric) for metric in "".join(metrics).split() if metric.isnumeric()]
        )
        gateways = [default for default in defaults if f"metric {metric}" in default]
        records = pattern.findall("".join(gateways))
    else:
        metric = 3
        records = pattern.findall("".join(defaults))
    addresses = [address for address in "".join(records).split() if address != "via"]
    return (metric - 1, addresses[0])


class Connection:
    """Uses anyd's client logic to query vpnm daemons functions over sockets."""

    session = JSONFileStorage("session")
    settings = JSONFileStorage("settings")
    settings["socks_port"] = settings.get("socks_port", 1080)
    settings["dns_port"] = settings.get("dns_port", 1053)
    settings["vpnmd_port"] = settings.get("vpnmd_port", 6554)
    vpnmd_address: Tuple[str, int] = ("localhost", settings["vpnmd_port"])
    subscrition = web_api.Subscrition()
    address: str = ""
    status: list = []

    def is_active(self) -> bool:
        status = (
            len(
                list(
                    filter(
                        systemd.is_active,
                        (
                            unit
                            for unit in [
                                self.session.get(key, "")
                                for key in self.session
                                if key in ["v2ray", "cloudflared", "tun2socks"]
                            ]
                        ),
                    )
                )
            )
            > 0
        )
        self.status.append(status)

        if self.session:
            try:
                proc = subprocess.run(
                    ["ip", "address", "show", f"tun{self.session['ifindex']}"],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError:
                status = False
            else:
                status = self.session["ifaddr"] in proc.stdout.decode()

            self.status.append(status)

            try:
                proc = subprocess.run(
                    ["ip", "link", "show", f"tun{self.session['ifindex']}"],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError:
                status = False
            else:
                status = "state UP" in proc.stdout.decode()

            self.status.append(status)

            proc = subprocess.run(["ip", "route"], check=True, capture_output=True)
            status = (
                self.session["node_address"]
                and f"default dev tun{self.session['ifindex']}" in proc.stdout.decode()
            )

            self.status.append(status)

            with ClientSession(self.vpnmd_address) as client:
                status = client.commit(
                    "iptables_rule_exists", str(self.settings["dns_port"])
                )

            self.status.append(status)

            self.address = get_actual_address()
            status = self.session["node_address"] == self.address

            self.status.append(status)

        return any(self.status)

    def stop(self):
        active_units = filter(
            systemd.is_active,
            (
                unit
                for unit in [
                    self.session.get(key, "")
                    for key in self.session
                    if key in ["v2ray", "cloudflared", "tun2socks"]
                ]
            ),
        )
        for unit in active_units:
            systemd.stop(unit)

        if self.session:
            with ClientSession(self.vpnmd_address) as client:
                client.commit("delete_iface", self.session["ifindex"])
                client.commit(
                    "delete_node_route",
                    self.session["node_address"],
                    self.session["default_gateway_address"],
                )
                client.commit("delete_dns_rule", str(self.settings["dns_port"]))

    def start(self, mode: str):
        self.subscrition.set_node(self.settings["socks_port"], mode)

        try:
            address = ipaddress.IPv4Address(
                self.subscrition.node["server"]["address"]
            ).exploded
        except ValueError:
            address = socket.gethostbyname(self.subscrition.node["server"]["host"])

        ifindex, ifaddr = _get_ifindex_and_ifaddr(
            self.session.get("ifindex"), self.session.get("ifaddr")
        )
        metric, default_gateway_address = _get_default_gateway_with_metric(ifindex)
        node_address = self.session.get("node_address")
        unit = self.session.get("v2ray", "")

        with ClientSession(self.vpnmd_address) as client:
            if node_address != address:
                response: subprocess.CompletedProcess = client.commit(
                    "add_node_route",
                    address,
                    default_gateway_address,
                    metric - 1,
                )

                response.check_returncode()
                self.session["node_address"] = address
                self.session["default_gateway_address"] = default_gateway_address
                self.session["default_gateway_metric"] = metric

                if systemd.is_active(unit):
                    systemd.stop(unit)

            if not systemd.is_active(unit):
                unit = systemd.run(
                    ["v2ray", "-config", self.subscrition.config.filepath.as_posix()]
                )
                self.session["v2ray"] = unit

            response = client.commit("add_iface", ifindex, ifaddr)
            response.check_returncode()
            self.session["ifindex"] = ifindex
            self.session["ifaddr"] = ifaddr
            unit = self.session.get("tun2socks", "")

            if not systemd.is_active(unit):
                unit = systemd.run(
                    [
                        "tun2socks-linux-amd64",
                        "-device",
                        f"tun://tun{ifindex}",
                        "-proxy",
                        f"socks5://127.0.0.1:{self.settings['socks_port']}",
                    ]
                )
                self.session["tun2socks"] = unit

            response = client.commit("set_iface_up", ifindex)
            response.check_returncode()

            response = client.commit("add_default_route", metric, ifindex)
            response.check_returncode()
            unit = self.session.get("cloudflared", "")

            if not systemd.is_active(unit):
                unit = systemd.run(
                    [
                        "cloudflared-linux-amd64",
                        "proxy-dns",
                        "--port",
                        str(self.settings["dns_port"]),
                    ],
                )
                self.session["cloudflared"] = unit

            while not self.address:
                proc = subprocess.run(
                    [
                        "dig",
                        "@127.0.0.1",
                        "-p",
                        str(self.settings["dns_port"]),
                        self.subscrition.node["server"]["host"],
                    ],
                    check=False,
                    capture_output=True,
                )
                if address in proc.stdout.decode():
                    self.address = address

            response = client.commit("add_dns_rule", str(self.settings["dns_port"]))
            response.check_returncode()
