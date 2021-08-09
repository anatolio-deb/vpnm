import argparse
import json
import zipfile
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen, SubprocessError
from threading import Thread
from urllib.request import Request, urlopen
from colorama import init, Fore


class GitHubAPI:
    filenames = [
                "tun2socks-linux-amd64.zip",
                "cloudflared-linux-amd64",
                "v2gen_amd64_linux",
                "vpnm",
                "vpnmd",
            ]
    urls = {}

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
            if asset["name"] in self.filenames:
                return asset

        raise KeyError("Asset not found")

    @staticmethod
    def _get_browser_download_url(asset: dict):
        return asset.get("browser_download_url")

    def _get_browser_download_urls(self) -> list:
        for url in self._get_api_request_urls():
            asset = self._get_asset(url)
            self.urls[asset["name"]] = self._get_browser_download_url(asset)


class Downloader:
    github_api = GitHubAPI()
    github_api.urls["v2ray-linux-64.zip"] = "https://github.com/v2ray/dist/raw/master/v2ray-linux-64.zip"
    bin_path = Path("/usr/local/bin")
    tmp_path = Path("/tmp")
    threads: list = []
    filenames = ["tun2socks-linux-amd64", "v2ray", 'geoip.dat', 'geosite.dat']

    @staticmethod
    def run(command: list):
        """Run a shell command"""
        with Popen(command, stdout=PIPE, stderr=STDOUT) as process:
            stdout = process.communicate()[0]

            if process.returncode != 0:
                raise SubprocessError(stdout.decode())

    def download(self, request: Request, filename: str):

        def unzip(filepath: str, target: str):
            """Extract the whole zip archive or an exact file from it.

            Args:
                filepath (str): The location of a zip file
                target (str, optional): The exact file to extract. Defaults to None.
            """

            with zipfile.ZipFile(filepath, "r") as zip_ref:
                for member in zip_ref.infolist():
                    if member.filename == target and not (
                        self.bin_path / member.filename
                        ).exists():
                        zip_ref.extract(member, self.bin_path)

        with urlopen(request) as response:

            if 'zip' in filename:

                filepath = self.tmp_path / filename

                with open(filepath, "wb") as file:
                    file.write(response.read())

                if 'v2ray' in filename:
                    
                    filename = self.filenames[1]

                    for member in self.filenames[1: ]:
                        unzip(filepath, member)
                        self.run(["chmod",  "ugo+r", (self.bin_path / member).as_posix()])
                else:
                    filename = self.filenames[0]
                    unzip(filepath, filename)
            else:

                with open(self.bin_path / filename, "wb") as file:
                    file.write(response.read())
            
            self.run(["chmod", "ugo+x", (self.bin_path / filename).as_posix()])
            

    def process_urls(self):
        for filename, url in self.github_api.urls.items():
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            thread = Thread(
                target=self.download,
                args=(
                    request,
                    filename,
                ),
            )
            thread.start()
            self.threads.append(thread)

        for thread in self.threads:
            thread.join()


class Installer:
    unit_path = Path("/etc/systemd/system/vpnmd.service")
    unit_content = f"""[Unit]
Description=VPN Manager daemon
After=network-online.target
Wants=network-online.target

[Service]
Restart=on-failure
ExecStart={Downloader.bin_path}/{GitHubAPI.filenames[-1]}

[Install]
WantedBy=multi-user.target"""
    install_commands = ["systemctl daemon-reload", f"systemctl enable --now {GitHubAPI.filenames[-1]}"]
    uninstall_commands = [f"systemctl disable --now {GitHubAPI.filenames[-1]}", "rm {}"]
    paths = [Downloader.bin_path / filename for filename in GitHubAPI.filenames + Downloader.filenames]

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
        print(Fore.CYAN + "Removing VPN Manager"  + Fore.RESET)
        installer.uninstall()
    else:
        downloader = Downloader()

        print("Welcome to" + Fore.CYAN + " VPN Manager!" + Fore.RESET)
        print()
        print("This will download and install the latest version of" + Fore.CYAN + " vpnm," + Fore.RESET)
        print("an alternative CLI client for" + Fore.CYAN + " VPN Manager." + Fore.RESET)
        print()
        print("It will add the `vpnm` command to system's bin directory, located at:")
        print()
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