"""Run the systemd transient services"""
import pathlib
import subprocess
from abc import ABCMeta, abstractmethod
from typing import Iterable

import requests


def check_ip() -> str:
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


class Systemd:
    """A wrapper around 'systemd-run' command.
    Manages transient systemd services with a subprocess facilities.
    """

    def __init__(self, user_mode: bool = False) -> None:
        if user_mode:
            user_flag = "--user"
        else:
            user_flag = ""
        self._cmd = [
            "systemd-run",
            f"{user_flag}",
            "--no-block",
            "-p",
            "Restart=on-failure",
        ]
        self.user_mode = user_mode
        self._user_flag = user_flag

    def run(self, cmd: Iterable, env: dict = None) -> str:
        """Run a transient systemd service

        Args:
            cmd (Iterable): The command to run inside a systemd unit
            known as ExecStart
            options (dict, optional): systemd service's envirnoment
            variables. Defaults to {}.

        Returns:
            str: The name of created unit file
        """
        if env:
            for key, value in env.items():
                self._cmd.extend(["-p", f"{key}={value}"])

        self._cmd.extend(cmd)

        proc = subprocess.run(
            self._cmd,
            check=True,
            capture_output=True,
        )

        self._cmd = [
            "systemd-run",
            f"{self._user_flag}",
            "--no-block",
            "-p",
            "Restart=on-failure",
        ]

        return proc.stderr.decode().split(":")[1].strip()

    def is_active(self, unit: str) -> bool:
        try:
            proc = subprocess.run(
                ["systemctl", f"{self._user_flag}", "is-active", f"{unit}"],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            return False
        else:
            if "active" in proc.stdout.decode():
                return True
        return False

    def stop(self, unit: str) -> None:
        subprocess.run(
            ["systemctl", f"{self._user_flag}", "stop", f"{unit}"],
            check=True,
            capture_output=True,
        )
