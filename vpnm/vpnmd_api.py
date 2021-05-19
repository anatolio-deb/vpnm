from __future__ import annotations

import ipaddress
import json
import subprocess

import simple_term_menu
import web_api
from sockets_framework import Session as Client
from web_api import AbstractPath


def _get_original_gateway() -> str:
    """Find the default route in a routing table with a minimal priority
    excluding the one to tun2socks if it exists"""
    proc = subprocess.run("ip route".split(), check=True, capture_output=True)
    priorities = {}
    for record in proc.stdout.decode().split("\n"):
        if "default" in record and "10.0.0.1" not in record:
            metric: str = ""
            for param in record.split():
                try:
                    address = ipaddress.IPv4Address(param)
                except ipaddress.AddressValueError:
                    if metric:
                        break
                else:
                    metric = record[record.find("metric") :].split()[-1]
                    if metric.isnumeric():
                        priorities[address.exploded] = int(metric)
    return min(priorities)


class Session(AbstractPath):
    file = AbstractPath.root / "session.json"
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
    original_gateway = _get_original_gateway()
    remote = ("localhost", 4000)
    route_priorities: list[int] = []
    args = "systemd-run --user --no-block -p Restart=on-failure"
    session = Session()
    ifname = "tun0"
    ifaddr = "10.0.0.2"
    tun2socks_addr = "10.0.0.1"

    @staticmethod
    def _stop(unit: str):
        subprocess.run(
            f"systemctl --user stop {unit}".split(),
            check=True,
            capture_output=False,
        )

    @staticmethod
    def is_active(unit: str) -> bool:
        proc = subprocess.run(
            f"systemctl --user is-active {unit}".split(),
            check=False,
            capture_output=True,
        )
        if proc.stdout.decode().strip() == "active":
            return True
        return False

    def stop(self):
        for unit in (
            self.session.data.get("badvpn-tun2socks", {}).get("unit"),
            self.session.data.get("v2ray", {}).get("unit"),
        ):
            if unit and self.is_active(unit):
                self._stop(unit)

        with Client(self.remote) as client:
            client.commit("delete_tuntap")

            node_address = self.session.data.get("v2ray", {}).get("address")

            if node_address:
                client.commit("delete_node_route", node_address, self.original_gateway)

    def start(self):
        with Client(self.remote) as client:
            client.commit("add_tuntap")
            client.commit("add_ifaddr")

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

            with open("/tmp/config.json", "w") as file:
                json.dump(node.config, file)

            with open("/tmp/config.json", "r") as file:
                config = json.load(file)

            unit = self.session.data.get("v2ray", {}).get("unit")

            if unit and self.is_active(unit) and config != node.config:
                self._stop(unit)

            if not unit or not self.is_active(unit):
                proc = subprocess.run(
                    f"{self.args} v2ray -config /tmp/config.json".split(),
                    check=True,
                    capture_output=True,
                )

                self.session.data = {
                    "v2ray": {
                        "unit": proc.stderr.decode().split(":")[1].strip(),
                        "address": node.address,
                    }
                }

            unit = self.session.data.get("badvpn-tun2socks", {}).get("unit")

            if not unit or not self.is_active(unit):
                proc = subprocess.run(
                    f"{self.args} \
                    badvpn-tun2socks \
                    --tundev {self.ifname} \
                    --netif-ipaddr {self.tun2socks_addr} \
                    --netif-netmask 255.255.255.0 \
                    --socks-server-addr 127.0.0.1:1080".split(),
                    check=True,
                    capture_output=True,
                )

                self.session.data = {
                    "badvpn-tun2socks": {
                        "unit": proc.stderr.decode().split(":")[1].strip()
                    }
                }

            client.commit("set_if_up")
            client.commit("add_node_route", node.address, self.original_gateway)
            client.commit("add_default_route")

            self.node = node
