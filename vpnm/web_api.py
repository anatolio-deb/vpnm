from __future__ import annotations

import requests

from vpnm.utils import JSONFileStorage


class Auth:
    api_url = "https://ssle2.ru/api/"
    secret = JSONFileStorage("secret")
    account: dict = {}

    def set_secret(self, email: str, password: str):
        if not self.secret:
            response = requests.post(
                f"{self.api_url}/token", data={"email": email, "passwd": password}
            )
            if response.json().get("msg") == "ok":
                self.secret["token"] = response.json().get("data")
            else:
                raise requests.exceptions.HTTPError(response.json().get("msg"))

    def set_account(self):
        user_id = self.secret.get("user_id")
        token = self.secret.get("token")

        if not self.account:
            response = requests.get(
                f"{self.api_url}user4/{user_id}?access_token={token}"
            )
            if response.json()["msg"] == "ok":
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
