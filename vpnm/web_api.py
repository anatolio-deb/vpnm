"""Web-related functionality such as token-based authentication and
nodes subscrition parsing.

Raises:
    requests.exceptions.HTTPError: Unnable to get authentication
    data in Auth class.
"""
from __future__ import annotations

import json
import subprocess
from random import randint
from threading import Thread
from typing import Dict

from simple_term_menu import TerminalMenu
from vpnmauth import VpnmApiClient

from vpnm import templates
from vpnm.utils import CONFIG, SECRET


def is_authenticated() -> bool:
    return bool(SECRET.exists() and SECRET.read_text())


class Subscrition:
    nodes: list = []
    node: Dict = {}
    threads: list[Thread] = []
    config: Dict = {}
    host: str

    def __init__(self) -> None:
        if is_authenticated():
            with open(SECRET, "r", encoding="utf-8") as file:
                secret = json.load(file)

            self.api_client = VpnmApiClient(
                api_url="https://ssle4.ru/api", token=secret["token"]
            )

    def _ping(self, node: dict) -> None:
        if node["server"][0][1] == "443":
            host = node["server"][1]["server"]
        else:
            host = node["server"][0][0]
        try:
            proc = subprocess.run(
                ["ping", "-c", "1", host],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            self.nodes[self.nodes.index(node)]["latency"] = 0
        else:
            self.nodes[self.nodes.index(node)]["latency"] = float(
                [time for time in proc.stdout.decode().split() if "time" in time][
                    0
                ].split("=")[1]
            )

    def set_node(
        self,
        socks_port: int,
        mode: str,
    ):
        response = self.api_client.nodes
        self.nodes = response["data"]["node"]

        for node in self.nodes:
            thread = Thread(target=self._ping, args=(node,))
            thread.start()
            self.threads.append(thread)

        for thread in self.threads:
            thread.join()

        self.nodes = sorted(
            list(
                filter(
                    lambda node: node["latency"] > 1,
                    self.nodes,
                )
            ),
            key=lambda node: node["latency"],
        )

        if mode == "best":
            index = 0
        elif mode == "random":
            index = randint(0, len(self.nodes))
        else:
            max_len = max([len(node["name"]) for node in self.nodes])
            menu = TerminalMenu(
                [
                    f"{node['name']}{' '*((max_len-len(node['name']))+1)}\
                        {int(node['latency'])} ms"
                    for node in self.nodes
                ],
                clear_screen=True,
                title="Available locations",
            )
            index = menu.show()

        self.node = self.nodes[index]

        if self.node["server"][0][1] == "443":
            self.host = self.node["server"][1]["server"]
            config = templates.PORT_443
            config["outbounds"][0]["settings"]["vnext"][0]["address"] = self.node[
                "server"
            ][1]["server"]
            config["outbounds"][0]["streamSettings"]["security"] = self.node["server"][
                0
            ][3]
            config["outbounds"][0]["streamSettings"]["network"] = self.node["server"][
                0
            ][4]
            config["outbounds"][0]["streamSettings"]["wsSettings"]["headers"][
                "Host"
            ] = self.host
            config["outbounds"][0]["streamSettings"]["wsSettings"]["path"] = self.node[
                "server"
            ][1]["path"]
            config["outbounds"][0]["streamSettings"]["tlsSettings"][
                "serverName"
            ] = self.host
        else:
            self.host = self.node["server"][0][0]
            config = templates.PORT_NON_443
            config["outbounds"][0]["settings"]["vnext"][0]["address"] = self.node[
                "server"
            ][0][0]
            config["outbounds"][0]["streamSettings"]["network"] = self.node["server"][
                0
            ][3]

        config["outbounds"][0]["settings"]["vnext"][0]["users"][0]["id"] = response[
            "data"
        ]["user_id"]
        config["outbounds"][0]["settings"]["vnext"][0]["port"] = int(
            self.node["server"][0][1]
        )
        config["outbounds"][0]["settings"]["vnext"][0]["users"][0]["alterId"] = int(
            self.node["server"][0][2]
        )
        config["inbounds"] = [
            {
                "listen": "127.0.0.1",
                "port": int(socks_port),
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True, "userLevel": 8},
                "sniffing": {"destOverride": [], "enabled": False},
                "tag": "socks",
            },
        ]

        with open(CONFIG, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)
