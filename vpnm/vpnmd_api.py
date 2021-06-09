from __future__ import annotations

import ipaddress
import json
import pathlib
import re
import socket
import subprocess
from typing import Tuple

from sockets_framework import Session as Client

from . import systemd, web_api
from .utils import get_actual_address

PRIVATE_NETWORKS = [
    "10.0.0.0/8",
    "100.64.0.0/10",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "198.18.0.0/15",
]


def _get_ifindex_and_ifaddr(ifindex: int, ifaddr: str) -> Tuple:
    proc = subprocess.run(["ip", "a"], check=True, capture_output=True)

    if f"tun{ifindex}" and ifaddr in proc.stdout.decode() and ifaddr:
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

    for network in PRIVATE_NETWORKS:
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


class Session(web_api.AbstractPath):
    _data: dict = {}

    @staticmethod
    def get_file() -> pathlib.Path:
        return web_api.AbstractPath.root / "session.json"

    def __init__(self) -> None:
        super().__init__()
        if self.get_file().exists():
            self._load_session()

    def _load_session(self):
        with self.get_file().open("r") as file:
            self._data = json.load(file)

    @property
    def data(self) -> dict:
        return self._data

    @data.setter
    def data(self, new_data: dict):
        self.data.update(new_data)
        with self.get_file().open("w") as file:
            json.dump(self.data, file, indent=4, sort_keys=True)
        self._load_session()


class Connection:
    auth = web_api.Auth()
    secret = web_api.Secret()
    remote = ("localhost", 4000)
    session = Session()
    dns_port = 1053
    socks_port = 1080
    config = "/tmp/config.json"
    address: str = ""

    def is_active(self):
        with Client(self.remote) as client:
            node_address = client.commit("get_node_address")

        self.address = get_actual_address()

        if node_address == self.address:
            return True
        return False

    def stop(self):
        for unit in (
            self.session.data.get("v2ray", ""),
            self.session.data.get("tun2socks", ""),
            self.session.data.get("cloudflared", ""),
        ):
            if systemd.is_active(unit):
                systemd.stop(unit)

        with Client(self.remote) as client:
            client.commit("delete_iface")
            client.commit("delete_node_route")
            client.commit("delete_dns_rule")

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

        subprocess.run(cmd, check=True)

        with open(self.config, "r") as file:
            config = json.load(file)

        host = config["outbounds"][0]["settings"]["vnext"][0]["address"]
        address = socket.gethostbyname(host)

        with Client(self.remote) as client:
            ifindex, ifaddr = client.commit("get_ifindex_and_ifaddr")
            ifindex, ifaddr = _get_ifindex_and_ifaddr(ifindex, ifaddr)
            metric, default_gateway_address = _get_default_gateway_with_metric(ifindex)
            client.commit(
                "add_node_route", address, default_gateway_address, metric - 1
            )
            client.commit("add_iface", ifindex, ifaddr)
            unit = self.session.data.get("tun2socks", "")

            if not systemd.is_active(unit):
                unit = systemd.run(
                    [
                        "tun2socks-linux-amd64",
                        "-device",
                        f"tun://tun{ifindex}",
                        "-proxy",
                        f"socks5://127.0.0.1:{self.socks_port}",
                    ]
                )
                self.session.data = {"tun2socks": unit}

            client.commit("set_iface_up")
            client.commit("add_default_route", metric)

            node_address = client.commit("get_node_address")

            if address != node_address and systemd.is_active(unit):
                systemd.stop(unit)

            unit = self.session.data.get("v2ray", "")

            if not systemd.is_active(unit):
                unit = systemd.run(["v2ray", "-config", self.config])
                self.session.data = {"v2ray": unit}

            unit = self.session.data.get("cloudflared", "")

            if not systemd.is_active(unit):
                unit = systemd.run(
                    ["cloudflared", "proxy-dns", "--port", str(self.dns_port)],
                )
                self.session.data = {"cloudflared": unit}

            while not self.address:
                proc = subprocess.run(
                    ["dig", "@127.0.0.1", "-p", str(self.dns_port), host],
                    check=False,
                    capture_output=True,
                )
                if address in proc.stdout.decode():
                    self.address = address

            client.commit("add_dns_rule", str(self.dns_port))
