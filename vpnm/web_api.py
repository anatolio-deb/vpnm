from __future__ import annotations

import json

import requests

from vpnm.utils import AbstractPath


class Secret(AbstractPath):
    @staticmethod
    def get_file():
        return AbstractPath.root / "secret.json"

    @property
    def data(self):
        if self.get_file().exists():
            with self.get_file().open("r") as file:
                return json.load(file)
        return {}

    @data.setter
    def data(self, data: str):
        with self.get_file().open("w") as file:
            json.dump(data, file)


def get_prompt_desicion():
    """A helper function to pass a value to click framework's click_option decorator.
    Helps to decide wether to prompt user's email and pasword to get a new web token.

    Returns:
        bool: True if there's no secret file on the clients filesystem, else False
    """
    if Secret.get_file().exists():
        return False
    return True


class Auth:
    apis = (
        "https://ssle.ru/api/",
        "https://ddnn.ru/api/",
        "https://vm-vpnm.appspot.com/",
        "https://ssle2.ru/api/",
    )
    _secret = Secret()
    secret: dict = _secret.data
    account: dict = {}

    def set_secret(self, email: str, password: str):
        for api in self.apis:
            if not self.secret:
                try:
                    response = requests.post(
                        f"{api}/token", data={"email": email, "passwd": password}
                    )
                except requests.RequestException:
                    if api is self.apis[-1]:
                        raise
                else:
                    if response.json().get("msg") == "ok":
                        self.secret = response.json().get("data")
                    elif api is self.apis[-1]:
                        raise requests.exceptions.HTTPError(response.json().get("msg"))

            else:
                break
        self._dump_secret()

    def _dump_secret(self):
        self._secret.data = self.secret

    def set_account(self):
        user_id = self._secret.data.get("user_id")
        token = self._secret.data.get("token")

        for api in self.apis:
            if not self.account:
                try:
                    response = requests.get(
                        f"{api}user4/{user_id}?access_token={token}"
                    )
                except requests.exceptions.RequestException:
                    if api is self.apis[-1]:
                        raise
                else:
                    if response.json()["msg"] == "ok":
                        self.account = response.json().get("data")
                    elif api is self.apis[-1]:
                        raise requests.exceptions.HTTPError(response.json().get("msg"))
            else:
                break
