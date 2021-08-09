import os
import pathlib
from abc import ABCMeta, abstractmethod

import requests


def get_location(address: str) -> dict:
    try:
        response = requests.get(f"http://ip-api.com/json/{address}")
    except requests.exceptions.RequestException:
        return {}
    else:
        return response.json()


def get_actual_address() -> str:
    """Requests the client's IP address from https://api.ipify.org via HTTP GET

    Returns:
        str: Client's IP address or 'unknown'
    """
    try:
        response = requests.get("https://api.ipify.org/")
    except requests.exceptions.RequestException:
        return "unknown"
    else:
        return response.text


class AbstractPath(metaclass=ABCMeta):
    root = pathlib.Path().home() / ".config/vpnm/"
    _data: dict = {}

    @staticmethod
    @abstractmethod
    def get_file():
        pass

    def __init__(self) -> None:
        if not self.root.exists():
            os.makedirs(self.root)

    @property
    @abstractmethod
    def data(self):
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AbstractPath:
            attrs = set(dir(C))
            if set(cls.__abstractmethods__) <= attrs:
                return True
        return NotImplemented
