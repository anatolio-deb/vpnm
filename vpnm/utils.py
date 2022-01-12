"""Utility functions and classess such as checking IP address and location,
and File storage"""
import json
import pathlib

import requests

CONFROOT = pathlib.Path().home()
CONFDIR = CONFROOT / ".config"
VPNMDIR = CONFDIR / "vpnm"
SECRET = VPNMDIR / "secret.json"
SESSION = VPNMDIR / "session.json"
SETTINGS = VPNMDIR / "settings.json"
CONFIG = VPNMDIR / "config.json"


def init():
    if not CONFDIR.exists():
        CONFDIR.mkdir()
    if not VPNMDIR.exists():
        VPNMDIR.mkdir()
    if not SETTINGS.exists():
        with open(SETTINGS, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "socks_port": 1080,
                    "dns_port": 1053,
                    "vpnmd_port": 6554,
                },
                file,
            )


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
