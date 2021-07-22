import json
import zipfile
from http.client import IncompleteRead
from string import Template
from subprocess import PIPE, STDOUT, Popen, TimeoutExpired
from threading import Thread
from typing import Any, Callable, Tuple
from urllib.request import Request, urlopen


class GitHubAPI:
    def __init__(self) -> None:
        self.browser_download_urls = self._get_browser_download_urls()

    @staticmethod
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

    @staticmethod
    def _get_json_response(api_request_url: str) -> dict:
        request = Request(api_request_url, headers={"User-Agent": "Mozilla/5.0"})

        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get_asset(self, api_request_url: str) -> dict:
        for asset in self._get_json_response(api_request_url)["assets"]:
            if asset["name"] in [
                "tun2socks-linux-amd64.zip",
                "cloudflared-linux-amd64",
                "v2gen_amd64_linux",
                "vpnm",
                "vpnmd",
            ]:
                return asset

        raise KeyError("Asset not found")

    @staticmethod
    def _get_browser_download_url(asset: dict):
        return asset.get("browser_download_url")

    def _get_browser_download_urls(self) -> list:
        return [
            self._get_browser_download_url(self._get_asset(url))
            for url in self._get_api_request_urls()
        ]


class Downloader:
    github_api = GitHubAPI()
    urls = github_api.browser_download_urls
    urls.append("https://github.com/v2ray/dist/raw/master/v2ray-linux-64.zip")
    bin_path = "/usr/local/bin"
    tmp_path = "/tmp"
    threads: list = []
    unit_path = "/etc/systemd/system/vpnmd.service"
    unit_content = """[Unit]
Description=VPN Manager daemon
After=network-online.target
Wants=network-online.target

[Service]
Restart=on-failure
ExecStart=/usr/local/bin/vpnmd

[Install]
WantedBy=multi-user.target"""

    @staticmethod
    def chmod(filepath: str):
        with Popen(["chmod", "+x", filepath], stdout=PIPE, stderr=STDOUT) as process:
            stdout = process.communicate()[0]

            if process.returncode != 0:
                raise RuntimeError(stdout)

    def unzip(self, filepath: str):
        with zipfile.ZipFile(filepath, "r") as zip_ref:
            zip_ref.extractall(self.bin_path)

    @staticmethod
    def get_filename_from_url(url: str) -> str:
        return url[-url[::-1].find("/") :]

    def get_filepath_from_filename(
        self, filename: str
    ) -> Tuple[str, Callable[[str], Any]]:
        if ".zip" in filename:
            return (f"{self.tmp_path}/{filename}", self.unzip)

        return (f"{self.bin_path}/{filename}", self.chmod)

    @staticmethod
    def download(request: Request, filepath: str, callback=None):

        with urlopen(request) as response:
            with open(filepath, "wb") as file:
                file.write(response.read())

        if callback is not None:
            callback(filepath)

    def process_urls(self):
        for url in self.urls:
            filename = self.get_filename_from_url(url)
            filepath, callback = self.get_filepath_from_filename(filename)
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            thread = Thread(
                target=self.download,
                args=(
                    request,
                    filepath,
                    callback,
                ),
            )
            thread.start()
            self.threads.append(thread)

        for thread in self.threads:
            thread.join()

        self.post_process()

    def post_process(self):
        with open(self.unit_path, "w") as file:
            file.write(self.unit_content)

        with Popen(
            ["systemctl", "daemon-reload"], stdout=PIPE, stderr=STDOUT
        ) as process:
            stdout = process.communicate()[0]

            if process.returncode != 0:
                raise RuntimeError(stdout)

        with Popen(
            ["systemctl", "enable", "--now", "vpnmd"], stdout=PIPE, stderr=STDOUT
        ) as process:
            stdout = process.communicate()[0]

            if process.returncode != 0:
                raise RuntimeError(stdout)

    def runner(self):
        print(
            f"""Welcome to VPN Manager!

This will download and install the latest version of vpnm,
an alternative CLI client for VPN Manager.

It will add the `vpnm` command to system's bin directory, located at:

{self.bin_path}

You can uninstall at any time by executing this script with the --uninstall option,
and these changes will be reverted."""
        )

        try:
            self.process_urls()
            self.post_process()
        except (ConnectionError, RuntimeError, TimeoutExpired, IncompleteRead) as ex:
            print(ex)
        else:
            print(
                """VPN Manager is installed now. Great!

You can test that everything is set up by executing:

`vpnm --help`"""
            )


if __name__ == "__main__":
    downloader = Downloader()
    downloader.runner()
