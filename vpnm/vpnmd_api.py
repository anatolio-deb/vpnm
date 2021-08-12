from __future__ import annotations

import ipaddress
import json
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
    session = JSONFileStorage("session")
    settings = JSONFileStorage("settings")
    settings["socks_port"] = settings.get("socks_port", "1080")
    settings["dns_port"] = settings.get("dns_port", "1053")
    settings["vpnmd_port"] = settings.get("vpnmd_port", 6554)
    vpnmd_address = ("localhost", settings["vpnmd_port"])
    auth = web_api.Auth()
    config = "/tmp/config.json"
    address: str = ""

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

            proc = subprocess.run(["ip", "route"], check=True, capture_output=True)
            status = self.session["node_address"] in proc.stdout.decode()
            proc = subprocess.run(["ip", "route"], check=True, capture_output=True)
            status = f"default dev tun{self.session['ifindex']}" in proc.stdout.decode()

            with ClientSession(self.vpnmd_address) as client:
                status = client.commit(
                    "iptables_rule_exists", self.settings["dns_port"]
                )

            self.address = get_actual_address()
            status = self.session["node_address"] == self.address

        return status

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
                client.commit("delete_dns_rule", self.settings["dns_port"])

    def start(self, mode: str = "", ping: bool = False):
        self.auth.set_account()
        link = self.auth.account["v2ray"] + "?mu=2"
        cmd = [
            "v2gen_amd64_linux",
            "-loglevel",
            "error",
            "-u",
            link,
            "-o",
            self.config,
        ]

        if not ping and mode != "-best":
            cmd.append("-ping=false")
        else:
            cmd.extend(["-c", "1"])
        if mode:
            cmd.append(mode)

        subprocess.run(cmd, check=True, capture_output=True)

        if not mode:
            subprocess.run(["clear"], check=True)

        with open(self.config, "r") as file:
            config = json.load(file)

        host = config["outbounds"][0]["settings"]["vnext"][0]["address"]
        address = socket.gethostbyname(host)

        if address == "127.0.0.1":
            raise ValueError(address)

        if self.settings["socks_port"] != "1080":
            config["inbounds"][0]["port"] = self.settings["socks_port"]

            with open(self.config, "w") as file:
                json.dump(config, file)

        with ClientSession(self.vpnmd_address) as client:
            ifindex, ifaddr = _get_ifindex_and_ifaddr(
                self.session.get("ifindex"), self.session.get("ifaddr")
            )
            metric, default_gateway_address = _get_default_gateway_with_metric(ifindex)
            node_address = self.session.get("node_address")
            unit = self.session.get("v2ray", "")

            if node_address != address:
                response = client.commit(
                    "add_node_route", address, default_gateway_address, metric - 1
                )

                assert isinstance(response, subprocess.CompletedProcess)
                response.check_returncode()
                self.session["node_address"] = address
                self.session["default_gateway_address"] = default_gateway_address
                self.session["default_gateway_metric"] = metric

                if systemd.is_active(unit):
                    systemd.stop(unit)

            if not systemd.is_active(unit):
                unit = systemd.run(["v2ray", "-config", self.config])
                self.session["v2ray"] = unit

            response = client.commit("add_iface", ifindex, ifaddr)
            assert isinstance(response, subprocess.CompletedProcess)
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
            assert isinstance(response, subprocess.CompletedProcess)
            response.check_returncode()

            response = client.commit("add_default_route", metric, ifindex)
            assert isinstance(response, subprocess.CompletedProcess)
            response.check_returncode()
            unit = self.session.get("cloudflared", "")

            if not systemd.is_active(unit):
                unit = systemd.run(
                    [
                        "cloudflared-linux-amd64",
                        "proxy-dns",
                        "--port",
                        self.settings["dns_port"],
                    ],
                )
                self.session["cloudflared"] = unit

            while not self.address:
                proc = subprocess.run(
                    ["dig", "@127.0.0.1", "-p", self.settings["dns_port"], host],
                    check=False,
                    capture_output=True,
                )
                if address in proc.stdout.decode():
                    self.address = address

            response = client.commit("add_dns_rule", self.settings["dns_port"])
            assert isinstance(response, subprocess.CompletedProcess)
            response.check_returncode()
