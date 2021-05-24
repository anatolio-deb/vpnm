"""Utility functions for cli.py.

Raises:
    RuntimeError: Module's not supposed to run standalone
"""
from __future__ import annotations

import socket

import requests
from utils import AbstractPath

APIS = ("https://ssle.ru/api/", "https://ddnn.ru/api/", "https://vm-vpnm.appspot.com/")


def get_token(email: str, password: str) -> requests.Response:
    """Requests a token from https://ssle.ru/api/token via HTTP POST

    Args:
        email (str): The client's email address registered at https://vpnm.ru
        password (str): The client's password

    Returns:
        requests.Response: A request containing a web token
    """
    for api in APIS:
        try:
            return requests.post(
                f"{api}/token", data={"email": email, "passwd": password}
            )
        except requests.RequestException as ex:
            exception = ex
    raise exception


def get_nodes(token: str) -> requests.Response:
    """Requests v2ray client's configurations from https://ssle.ru/api/ via HTTP GET

    Args:
        token (str): utils.get_token

    Returns:
        requests.Response: A request containing v2ray client's configurations as json
    """
    for api in APIS:
        try:
            return requests.get(f"{api}/node3?access_token={token}")
        except requests.RequestException as ex:
            exception = ex
    raise exception


class Secret(AbstractPath):
    file = AbstractPath.root / "secret"

    @property
    def data(self):
        if self.file.exists():
            with self.file.open("r") as file:
                return file.read()
        return None

    @data.setter
    def data(self, token: str):
        self.file.write_text(token)


def get_prompt_desicion():
    """A helper function to pass a value to click framework's click_option decorator.
    Helps to decide wether to prompt user's email and pasword to get a new web token.

    Returns:
        bool: True if there's no secret file on the clients filesystem, else False
    """
    if Secret.file.exists():
        return False
    return True


class Node:
    """Represents configuration for each node coming from utils.get_nodes"""

    config: str
    address: str
    socks_port: int = 1080

    def __init__(
        self,
        node_id,
        node_class,
        name,
        server,
        info,
        group,
        online_user,
        online,
        traffic_rate,
    ):
        self.node_id = node_id
        self.node_class = node_class
        self.name = name
        self.server = self.set_server(server)
        self.info = info
        self.group = group
        self.online_user = online_user
        self.online = online
        self.traffic_rate = traffic_rate
        self._set_config()
        self.host = self.server["host"]

    def set_address(self):
        self.address = socket.gethostbyname(self.server["host"])
        if self.address == "127.0.0.1":
            raise ValueError(
                f"{self.name} is not available due your DNS provider: \
                    {self.address}"
            )

    def _tls_or_auto(self):
        if "tls" in self.server:
            return self.server["security"]
        return "auto"

    def _set_config(self):
        user_id = "a7742a12-6012-3715-982b-d3a1d0c3eeef"
        if self.server:
            self.config = {
                "outbounds": [
                    {
                        "mux": {},
                        "protocol": "vmess",
                        "sendThrough": "0.0.0.0",
                        "settings": {
                            "vnext": [
                                {
                                    "address": self.server["host"],
                                    "port": 443,
                                    "users": [
                                        {
                                            "alterId": int(self.server["alterId"]),
                                            "id": user_id,
                                            "level": 0,
                                            "security": self._tls_or_auto(),
                                        }
                                    ],
                                }
                            ]
                        },
                        "streamSettings": {
                            "dsSettings": {"path": "/"},
                            "httpSettings": {"host": [], "path": "/"},
                            "kcpSettings": {
                                "congestion": False,
                                "downlinkCapacity": 20,
                                "header": {"type": "none"},
                                "mtu": 1350,
                                "readBufferSize": 1,
                                "tti": 20,
                                "uplinkCapacity": 5,
                                "writeBufferSize": 1,
                            },
                            "network": "ws",
                            "quicSettings": {
                                "header": {"type": "none"},
                                "key": "",
                                "security": "",
                            },
                            "security": "tls",
                            "sockopt": {"mark": 1},
                            "tcpSettings": {
                                "header": {
                                    "request": {
                                        "headers": {},
                                        "method": "GET",
                                        "path": [],
                                        "version": "1.1",
                                    },
                                    "response": {
                                        "headers": {},
                                        "reason": "OK",
                                        "status": "200",
                                        "version": "1.1",
                                    },
                                    "type": "none",
                                }
                            },
                            "tlsSettings": {
                                "allowInsecure": False,
                                "alpn": [],
                                "certificates": [],
                                "disableSystemRoot": False,
                                "serverName": "",
                            },
                            "wsSettings": {
                                "headers": {"Host": self.server["host"]},
                                "path": self.server["path"],
                            },
                        },
                        "tag": "outBound_PROXY",
                    }
                ],
                "inbounds": [
                    {
                        "protocol": "socks",
                        "listen": "127.0.0.1",
                        "port": self.socks_port,
                    }
                ],
            }

    @staticmethod
    def set_server(server: str) -> dict:
        """Formats a server objects of each node.

        Args:
            server (str): A server object of each node in utils.get_nodes.

        Returns:
            [dict]: Formated values
        """
        data = server.split("|")
        temp_list = list()
        temp_dict = dict()
        for value in data:
            if ";" in value:
                temp_list = value.split(";")
            elif "=" in value:
                temp_dict[value[: value.index("=")]] = value[value.index("=") + 1 :]
        for value in temp_list:
            if "=" in value:
                temp_dict[
                    temp_list.pop(temp_list.index(value))[: value.index("=")]
                ] = value[value.index("=") + 1 :]
            elif value == "tls":
                temp_dict["security"] = value
            elif value == "ws":
                temp_dict["network"] = value
            elif value.isnumeric() and int(value) > 0:
                temp_dict["alterId"] = value
        return temp_dict

    @staticmethod
    def get_node(node: dict):
        """A factory method to get a Node instances

        Args:
            node (dict): A nod object of each node from request of utils.get_nodes

        Returns:
            object: self
        """
        return Node(
            node["id"],
            node["class"],
            node["name"],
            node["server"],
            node["info"],
            node["group"],
            node["online_user"],
            node["online"],
            node["traffic_rate"],
        )


if __name__ == "__main__":
    raise RuntimeError("This module isn't standalone.")
