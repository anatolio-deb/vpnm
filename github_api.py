import json
from string import Template
from urllib.request import Request, urlopen


def _get_api_request_urls() -> list:
    api_request_template = Template(
        "https://api.github.com/repos/$user/$repository/releases/latest"
    )
    metadata = [
        ("xjasonlyu", "tun2socks"),
        ("cloudflare", "cloudflared"),
        ("iochen", "v2gen"),
        ("anatolio-deb", "vpnmd"),
        ("anatolio-deb", "vpnm"),
    ]

    return [
        api_request_template.substitute(user=user, repository=repository)
        for user, repository in metadata
    ]


def _get_json_response(api_request_url: str) -> dict:
    request = Request(api_request_url, headers={"User-Agent": "Mozilla/5.0"})

    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_asset(api_request_url: str) -> dict:
    for asset in _get_json_response(api_request_url)["assets"]:
        if asset["name"] in [
            "tun2socks-linux-amd64.zip",
            "cloudflared-linux-amd64",
            "v2gen_amd64_linux",
        ]:
            return asset

    raise KeyError("Asset not found")


def _get_browser_download_url(asset: dict):
    return asset.get("browser_download_url")


def get_browser_download_urls() -> list:
    return [
        _get_browser_download_url(_get_asset(url))
        for url in _get_api_request_urls()[:3]
    ]


if __name__ == "__main__":
    print(get_browser_download_urls())
