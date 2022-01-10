"""Utility functions and classess such as checking IP address and location,
and File storage"""
import json
import pathlib
from collections import UserDict

import requests


def get_location(address: str):
    location = ""

    try:
        response = requests.get(f"http://ip-api.com/json/{address}")
    except requests.exceptions.RequestException:
        data = {}
    else:
        data = response.json()
    finally:
        city = data.get("city")
        country = data.get("country")

        if city and country:
            location = f", {city}, {country}"

    return location


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


class JSONFileStorage(UserDict):
    """A file storage to store data in json format
    as well as keepeing the actual state in the memory."""

    root = pathlib.Path().home() / ".config"
    container = root / "vpnm"

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

        with open(self.filepath, "w", encoding="utf-8") as file:
            json.dump(self.data, file, sort_keys=True, indent=4)

    def __init__(self, filename: str) -> None:
        super().__init__()

        if ".json" not in filename:
            filename = f"{filename}.json"

        self.filepath = self.container / filename

        if not self.root.exists():
            self.root.mkdir()

        if not self.container.exists():
            self.container.mkdir()

        if not self.filepath.exists():
            self.filepath.touch()
        elif self.filepath.read_text():
            with open(self.filepath, "r", encoding="utf-8") as file:
                self.data = json.load(file)
