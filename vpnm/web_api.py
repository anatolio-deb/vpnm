"""Web-related functionality such as token-based authentication and
nodes subscrition parsing.

Raises:
    requests.exceptions.HTTPError: Unnable to get authentication
    data in Auth class.
"""
from __future__ import annotations

import base64
import json
import subprocess
from random import randint
from threading import Thread
from urllib.request import Request, urlopen

import requests
from simple_term_menu import TerminalMenu

from vpnm.utils import JSONFileStorage


class Auth:
    """Token-based authentication logic.

    Raises:
        requests.exceptions.HTTPError: Unnable to get authentication data.
    """

    api_url = "https://ssle3.ru/api/"
    secret = JSONFileStorage("secret")
    account: dict = {}

    def set_secret(self, email: str, password: str):
        if not self.secret:
            response = requests.post(
                f"{self.api_url}/token", data={"email": email, "passwd": password}
            )
            if response.json().get("msg") == "ok":
                self.secret["token"] = response.json()["data"]["token"]
                self.secret["user_id"] = response.json()["data"]["user_id"]
            else:
                raise requests.exceptions.HTTPError(response.json().get("msg"))

    def set_account(self):
        user_id = self.secret.get("user_id")
        token = self.secret.get("token")

        if not self.account:
            response = requests.get(
                f"{self.api_url}user4/{user_id}?access_token={token}"
            )
            if response.json().get("msg") == "ok":
                self.account = response.json().get("data")
            else:
                raise requests.exceptions.HTTPError(response.json().get("msg"))


def get_prompt_desicion() -> bool:
    """A helper function to pass a value to click framework's click_option decorator.
    Helps to decide wether to prompt user's email and pasword to get a new web token.

    Returns:
        bool: True if there's no secret file on the clients filesystem, else False
    """
    secret = JSONFileStorage("secret")

    if secret:
        return False
    return True


class Subscrition:
    """A logic to parse the nodes subscrition of VPN Manager backend.
    Thanks to folks from https://github.com/airborne007/v2sub.

    It has a template configuration which is dictionary with some pre-defined and
    non-defined values. This configuration is a v2ray node configuration that is
    stored on the filesystem as 'config.json' file and is passed to the v2ray core
    binary in the vpnmd_api.Connection. See Config Reference at:
    https:/v2fly.org/en_US/config/overview.html#overview

    Non-defined values are being defined from the parsed configuration data
    obtained from VPN Manager backend. There're many nodes coming from the subscrition
    link, but the configuration template is filled only for the node that
    the user choose in the vpnmd_api.Connection.

    The user choose a node from the list of all nodes coming from the subscrition link
    in the terminal menu by facilities of simple-term-menu package. See more at:
    https://pypi.org/project/simple-term-menu/.
    """

    nodes: list = []
    node: dict = {}
    threads: list[Thread] = []
    template: dict = {
        "inbound": {
            "listen": "127.0.0.1",
            "port": None,
            "protocol": "socks",
            "settings": {"auth": "noauth", "udp": True, "userLevel": 8},
            "sniffing": {"destOverride": [], "enabled": False},
            "tag": "socks",
        },
        "log": {"loglevel": "warning"},
        "outbound": {
            "mux": {"concurrency": 8, "enabled": False},
            "protocol": "vmess",
            "settings": {
                "vnext": [
                    {
                        "address": None,
                        "port": None,
                        "users": [
                            {
                                "alterId": None,
                                "encryption": "",
                                "flow": "",
                                "id": None,
                                "level": 8,
                                "security": "auto",
                            }
                        ],
                    }
                ]
            },
            "streamSettings": {
                "network": None,
                "security": None,
                "tlsSettings": {
                    "allowInsecure": False,
                    "serverName": None,
                },
                "wsSettings": {
                    "headers": {"Host": None},
                    "path": None,
                },
            },
            "tag": "proxy",
        },
    }
    config = JSONFileStorage("config")

    @staticmethod
    def _padding_base64(data):
        missing_padding = len(data) % 4
        if missing_padding != 0:
            data += b"=" * (4 - missing_padding)
        return data

    def update(self, url: str) -> None:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})

        with urlopen(request) as response:
            self.nodes = [
                json.loads(
                    base64.b64decode(node.decode().replace("vmess://", "")).decode()
                )
                for node in base64.b64decode(
                    self._padding_base64(response.read())
                ).splitlines()
            ]

    def _ping(self, node: dict) -> None:
        try:
            proc = subprocess.run(
                ["ping", "-c", "1", node["add"]], check=True, capture_output=True
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
            max_len = max([len(node["ps"]) for node in self.nodes])
            menu = TerminalMenu(
                [
                    f"{node['ps']}{' '*((max_len-len(node['ps']))+1)}\
                        {int(node['latency'])} ms"
                    for node in self.nodes
                ],
                clear_screen=True,
                title="Available locations",
            )
            index = menu.show()

        self.node = self.nodes[index]
        self.template["inbound"]["port"] = socks_port
        self.template["outbound"]["settings"]["vnext"][0]["address"] = self.node["add"]
        self.template["outbound"]["settings"]["vnext"][0]["port"] = self.node["port"]
        self.template["outbound"]["settings"]["vnext"][0]["users"][0][
            "alterId"
        ] = self.node["aid"]
        self.template["outbound"]["settings"]["vnext"][0]["users"][0]["id"] = self.node[
            "id"
        ]
        self.template["outbound"]["streamSettings"]["network"] = self.node["net"]
        self.template["outbound"]["streamSettings"]["security"] = self.node["tls"]
        self.template["outbound"]["streamSettings"]["tlsSettings"][
            "serverName"
        ] = self.node["host"]
        self.template["outbound"]["streamSettings"]["wsSettings"]["headers"][
            "Host"
        ] = self.node["host"]
        self.template["outbound"]["streamSettings"]["wsSettings"]["path"] = self.node[
            "path"
        ]

        if self.config != self.template:
            self.config["inbound"] = self.template["inbound"]
            self.config["log"] = self.template["log"]
            self.config["outbound"] = self.template["outbound"]
