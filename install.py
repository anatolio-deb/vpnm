import argparse
import json
from types import FunctionType
import zipfile
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen, SubprocessError
from threading import Thread
from typing import Tuple
from urllib.request import Request, urlopen
from colorama import init, Fore


class GitHubAPI:
    def __init__(self) -> None:
        self.browser_download_urls = self._get_browser_download_urls()

    @staticmethod
    def _get_api_request_urls() -> list:
        api_request_template = "https://api.github.com/repos/{}/{}/releases/latest"
        metadata = [
            ("xjasonlyu", "tun2socks"),
            ("cloudflare", "cloudflared"),
            ("iochen", "v2gen"),
            ("anatolio-deb", "vpnmd"),
            ("anatolio-deb", "vpnm"),
        ]

        return [
            api_request_template.format(user, repository)
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
    bin_path = Path("/usr/local/bin")
    tmp_path = Path("/tmp")
    threads: list = []

    @staticmethod
    def run(command: list):
        """Run a shell command"""
        with Popen(command, stdout=PIPE, stderr=STDOUT) as process:
            stdout = process.communicate()[0]

            if process.returncode != 0:
                raise SubprocessError(stdout.decode())

    @staticmethod
    def get_filename(url: str) -> str:
        return url[-url[::-1].find("/") :]

    def get_filepath_and_callback(self, filename: str) -> Tuple[Path, FunctionType]:
        def unzip(filepath: str, target: str):
            """Extract the whole zip archive or an exact file from it.

            Args:
                filepath (str): The location of a zip file
                target (str, optional): The exact file to extract. Defaults to None.
            """

            with zipfile.ZipFile(filepath, "r") as zip_ref:
                for member in zip_ref.infolist():
                    if member.filename == target:
                        zip_ref.extract(member, self.bin_path)

            if not (self.bin_path / target).exists():
                raise FileNotFoundError(f"{target} is not found in {filepath}")

        if self.tmp_path and ".zip" in filename:
            return (self.tmp_path / filename, unzip)
        return (self.bin_path / filename, self.run)

    def download(self, request: Request, filepath: str, callback: FunctionType):

        with urlopen(request) as response:
            with open(filepath, "wb") as file:
                file.write(response.read())
        
        if callback is not self.run:
            if "v2ray-linux-64.zip" in filepath:
                callback(filepath, "v2ray")
                filepath = self.bin_path / "v2ray"
            else:
                callback(filepath, "tun2socks-linux-amd64")
                filepath = self.bin_path / "tun2socks-linux-amd64"
            callback = self.run
        
        if callback is self.run:
            callback(["chmod", "ugo+x", filepath])

    def process_urls(self):
        for url in self.urls:
            filename = self.get_filename(url)
            filepath, callback = self.get_filepath_and_callback(filename)
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            thread = Thread(
                target=self.download,
                args=(
                    request,
                    filepath.as_posix(),
                    callback,
                ),
            )
            thread.start()
            self.threads.append(thread)

        for thread in self.threads:
            thread.join()


class Installer:
    unit_path = Path("/etc/systemd/system/vpnmd.service")
    unit_content = """[Unit]
Description=VPN Manager daemon
After=network-online.target
Wants=network-online.target

[Service]
Restart=on-failure
ExecStart=/usr/local/bin/vpnmd

[Install]
WantedBy=multi-user.target"""
    install_commands = ["systemctl daemon-reload", "systemctl enable --now vpnmd"]
    uninstall_commands = ["systemctl disable --now vpnmd", "rm {}"]
    filenames = [
        "cloudflared-linux-amd64",
        "tun2socks-linux-amd64",
        "v2gen_amd64_linux",
        "v2ray",
        "vpnm",
        "vpnmd",
    ]
    paths = [Downloader.bin_path / filename for filename in filenames]

    def install(self):
        with open(self.unit_path, "w") as file:
            file.write(self.unit_content)

        for command in self.install_commands:
            Downloader.run(command.split())

    def uninstall(self):
        for command in self.uninstall_commands:
            if command is self.uninstall_commands[0]:
                try:
                    Downloader.run(command.split())
                except SubprocessError as ex:
                    print(ex)
            else:
                self.paths.append(self.unit_path)
                for path in self.paths:
                    if path.exists() and path.is_file():
                        try:
                            Downloader.run(command.format(path).split())
                        except SubprocessError as ex:
                            print(ex)


if __name__ == "__main__":
    init()
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true", default=False)
    args = parser.parse_args()

    installer = Installer()

    if args.uninstall:
        print(Fore.CYAN + "Removing VPN Manager")
        installer.uninstall()
    else:
        downloader = Downloader()

        print("Welcome to" + Fore.CYAN + " VPN Manager!" + Fore.RESET)
        print()
        print("This will download and install the latest version of" + Fore.CYAN + " vpnm" + Fore.RESET)
        print("an alternative CLI client for" + Fore.CYAN + " VPN Manager." + Fore.RESET)
        print()
        print("It will add the `vpnm` command to system's bin directory, located at:")
        print(Fore.CYAN + downloader.bin_path.as_posix() + Fore.RESET)
        print()
        print("You can uninstall at any time by executing this script with the --uninstall option,")
        print("and these changes will be reverted.")
        print()
        print(Fore.CYAN + "Retrieving dependencies..." + Fore.RESET)
        print()
        
        downloader.process_urls()
        
        print(Fore.CYAN + "Installing VPN Manager..." + Fore.RESET)
        print()

        installer.install()

        print(Fore.CYAN + "VPN Manager is installed now. Great!" + Fore.RESET)
        print()
        print("You can test that everything is set up by executing:")
        print("`vpnm --help`")