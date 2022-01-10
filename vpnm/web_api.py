"""Web-related functionality such as token-based authentication and
nodes subscrition parsing.

Raises:
    requests.exceptions.HTTPError: Unnable to get authentication
    data in Auth class.
"""
from __future__ import annotations

import subprocess
from random import randint
from threading import Thread

from simple_term_menu import TerminalMenu
from vpnmauth import VpnmApiClient

from vpnm.utils import JSONFileStorage

from .templates import TEMPLATE_443, TEMPLATE_NON_443


def get_prompt_desicion() -> bool:
    """A helper function to pass a value to click framework's click_option decorator.
    Helname to decide wether to prompt user's email and pasword to get a new web token.

    Returns:
        bool: True if there's no secret file on the clients filesystem, else False
    """
    return not bool(JSONFileStorage("secret"))


class Subscrition:
    node: dict = {}
    nodes: list = []
    threads: list[Thread] = []
    config = JSONFileStorage("config")
    secret = JSONFileStorage("secret")
    api_client = VpnmApiClient(
        api_url="https://ssle4.ru/api", token=secret.get("token")
    )
    template: dict

    def _ping(self, node: dict) -> None:
        try:
            proc = subprocess.run(
                ["ping", "-c", "1", node["server"]["address"]],
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
        data = self.api_client.nodes
        self.nodes = data["node"]

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

        if self.node["server"]["port"] == "443":
            self.template = TEMPLATE_443
        else:
            self.template = TEMPLATE_NON_443

        self.template["outbounds"][0]["settings"]["vnext"][0]["address"] = self.node[
            "server"
        ]["address"]
        self.template["outbounds"][0]["settings"]["vnext"][0]["port"] = int(
            self.node["server"]["port"]
        )
        self.template["outbounds"][0]["settings"]["vnext"][0]["users"][0][
            "alterId"
        ] = int(self.node["server"]["alterId"])
        self.template["outbounds"][0]["settings"]["vnext"][0]["users"][0]["id"] = data[
            "user_id"
        ]
        self.template["outbounds"][0]["streamSettings"]["network"] = self.node[
            "server"
        ]["network"]
        self.template["outbounds"][0]["streamSettings"]["security"] = self.node[
            "server"
        ].get("security")
        self.template["outbounds"][0]["streamSettings"]["tlsSettings"][
            "serverName"
        ] = self.node["server"]["host"]
        self.template["outbounds"][0]["streamSettings"]["wsSettings"]["headers"][
            "Host"
        ] = self.node["server"]["host"]
        self.template["outbounds"][0]["streamSettings"]["wsSettings"][
            "path"
        ] = self.node["server"]["path"]

        if self.config != self.template:
            self.config["inbound"] = {
                "listen": "127.0.0.1",
                "port": socks_port,
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True, "userLevel": 8},
                "sniffing": {"destOverride": [], "enabled": False},
                "tag": "socks",
            }
            self.config["log"] = {"loglevel": "warning"}
            self.config["outbounds"] = self.template["outbounds"]
