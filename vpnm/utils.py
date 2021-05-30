"""Run the systemd transient services"""
import pathlib
from abc import ABCMeta, abstractmethod

import requests


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

    @property
    @abstractmethod
    def file(self) -> pathlib.Path:
        pass

    def __init__(self) -> None:
        if not self.root.exists():
            self.root.mkdir()

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
