from __future__ import annotations

import ipaddress
import json
import re
import subprocess
from typing import Tuple

import simple_term_menu
import web_api
from sockets_framework import Session as Client
from systemd_run_wrapper import Systemd


def _get_ifindex_and_ifaddr(ifindex: int, ifaddr: str) -> Tuple:
    proc = subprocess.run(["ip", "a"], check=True, capture_output=True)

    if ifaddr and ifindex:
        if ifaddr in proc.stdout.decode() and f"tun{ifindex}" in proc.stdout.decode():
            return (ifindex, ifaddr)

    pattern = re.compile(r"tun\d*")
    ifaces = pattern.findall(proc.stdout.decode())

    if not ifaces:
        ifindex = 0
    else:
        pattern = re.compile(r"\d*")
        ifindex = max(list(map(int, pattern.findall("".join(ifaces))))) + 1

    pattern = re.compile(r"\d*.\d*.\d*.\d*/\d*")
    nets = pattern.findall(proc.stdout.decode())

    reserved = [
        "10.0.0.0/8",
        "100.64.0.0/10",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "198.18.0.0/15",
    ]

    for network in reserved:
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
    metric = min(
        [int(metric) for metric in "".join(metrics).split() if metric.isnumeric()]
    )
    gateways = [default for default in defaults if f"metric {metric}" in default]
    pattern = re.compile(r"via \d*.\d*.\d*.\d*")
    records = pattern.findall("".join(gateways))
    addresses = [address for address in "".join(records).split() if address != "via"]
    return (metric - 1, addresses[0])


class Session(web_api.AbstractPath):
    file = web_api.AbstractPath.root / "session.json"
    _data: dict = {}

    def __init__(self) -> None:
        super().__init__()
        if self.file.exists():
            self._load_session()

    def _load_session(self):
        with self.file.open("r") as file:
            self._data = json.load(file)

    @property
    def data(self) -> dict:
        return self._data

    @data.setter
    def data(self, new_data: dict):
        self.data.update(new_data)
        with self.file.open("w") as file:
            json.dump(self.data, file, indent=4, sort_keys=True)
        self._load_session()


class Connection:
    nodes: list[web_api.Node] = []
    node: web_api.Node
    secret = web_api.Secret()
    remote = ("localhost", 4000)
    session = Session()
    systemd = Systemd(user_mode=True)
    dns_port = 1053
    socsk_port = web_api.Node.socks_port

    def stop(self):
        for unit in (
            self.session.data.get("v2ray", ""),
            self.session.data.get("tun2socks", ""),
            self.session.data.get("cloudflared", ""),
        ):
            if self.systemd.is_active(unit):
                self.systemd.stop(unit)

        with Client(self.remote) as client:
            client.commit("delete_iface")
            client.commit("delete_node_route")
            client.commit("delete_dns_rule")

    def start(self):
        response = web_api.get_nodes(self.secret.data)

        for data in response.json().get("data").get("node"):
            node = web_api.Node.get_node(data)
            if node.config:
                self.nodes.append(node)
        terminal_menu = simple_term_menu.TerminalMenu(
            [node.name for node in self.nodes]
        )
        menu_entry_index = terminal_menu.show()
        node = self.nodes[menu_entry_index]

        node.set_address()

        with Client(self.remote) as client:
            ifindex, ifaddr = client.commit("get_ifindex_and_ifaddr")
            ifindex, ifaddr = _get_ifindex_and_ifaddr(ifindex, ifaddr)
            metric, default_gateway_address = _get_default_gateway_with_metric(ifindex)
            client.commit(
                "add_node_route", node.address, default_gateway_address, metric - 1
            )
            client.commit("add_iface", ifindex, ifaddr)
            unit = self.session.data.get("tun2socks", "")

            if not self.systemd.is_active(unit):
                unit = self.systemd.run(
                    [
                        "tun2socks-linux-amd64",
                        "-device",
                        f"tun://tun{ifindex}",
                        "-proxy",
                        f"socks5://127.0.0.1:{self.socsk_port}",
                    ]
                )
                self.session.data = {"tun2socks": unit}

            client.commit("set_iface_up")
            client.commit("add_default_route", metric)

            unit = self.session.data.get("v2ray", "")

            try:
                with open("/tmp/config.json", "r") as file:
                    if json.load(file) != node.config:
                        if self.systemd.is_active(unit):
                            self.systemd.stop(unit)
                        raise FileNotFoundError
            except FileNotFoundError:
                with open("/tmp/config.json", "w") as file:
                    json.dump(node.config, file)
            finally:
                if not self.systemd.is_active(unit):
                    unit = self.systemd.run(["v2ray", "-config", "/tmp/config.json"])
                    self.session.data = {"v2ray": unit}

            unit = self.session.data.get("cloudflared", "")

            if not self.systemd.is_active(unit):
                unit = self.systemd.run(
                    ["cloudflared", "proxy-dns", "--port", str(self.dns_port)],
                )
                self.session.data = {"cloudflared": unit}

            while True:
                proc = subprocess.run(
                    ["dig", "@127.0.0.1", "-p", str(self.dns_port), node.host],
                    check=False,
                    capture_output=True,
                )
                if node.address in proc.stdout.decode():
                    break

            client.commit("add_dns_rule", str(self.dns_port))

        self.node = node
