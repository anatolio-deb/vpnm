import argparse
import json
import zipfile
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen, SubprocessError
from threading import Thread
from urllib.request import Request, urlopen


class GitHubAPI:
    filenames = [
        "tun2socks-linux-amd64.zip",
        "v2ray-linux-64.zip",
        "cloudflared-linux-amd64",
        "v2gen_amd64_linux",
        "vpnmd",
        "vpnm",
    ]
    data: dict = {}

    def __init__(self) -> None:
        self._set_data()

    @staticmethod
    def _get_api_request_urls() -> list:
        api_request_template = "https://api.github.com/repos/{}/{}/releases/latest"
        metadata = [
            ("xjasonlyu", "tun2socks"),
            ("cloudflare", "cloudflared"),
            ("iochen", "v2gen"),
            ("v2fly", "v2ray-core"),
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

    def _set_data(self):
        for response in self._get_api_request_urls():
            if response["asset"]["name"] in self.filenames:
                self.data[response["asset"]["name"]] = {
                    "url": response["asset"]["browser_download_url"],
                    "version": response["tag_name"],
                }


class Downloader:
    github_api = GitHubAPI()
    bin_path = Path("/usr/local/bin")
    tmp_path = Path("/tmp")
    threads: list = []
    filenames = ["tun2socks-linux-amd64", "v2ray", "geoip.dat", "geosite.dat"]

    @staticmethod
    def run(command: list):
        """Run a shell command"""
        with Popen(command, stdout=PIPE, stderr=STDOUT) as process:
            stdout = process.communicate()[0]

            if process.returncode != 0:
                raise SubprocessError(stdout.decode())

        return stdout.decode()

    def download(self, request: Request, filename: str, version: str):
        def unzip(filepath: Path, target: str):
            """Extract the whole zip archive or an exact file from it.

            Args:
                filepath (str): The location of a zip file
                target (str, optional): The exact file to extract. Defaults to None.
            """

            with zipfile.ZipFile(filepath, "r") as zip_ref:
                for member in zip_ref.infolist():
                    if member.filename == target:
                        zip_ref.extract(member, self.bin_path)

        _filename = ""

        if filename == "tun2socks-linux-amd64.zip":
            _filename = self.filenames[0]

            def callback(filepath: Path) -> None:
                unzip(filepath, self.filenames[0])

        elif filename == "v2ray-linux-64.zip":
            _filename = self.filenames[1]

            def callback(filepath: Path) -> None:
                for member in self.filenames[1:]:
                    unzip(filepath, member)
                    self.run(["chmod", "ugo+r", (self.bin_path / member).as_posix()])

        else:

            def callback(filepath: Path) -> None:
                self.run(["chmod", "ugo+x", filepath.as_posix()])

        if not _filename:
            filepath = self.bin_path / filename
        else:
            filepath = self.bin_path / _filename

        if filename == GitHubAPI.filenames[3]:
            cmd = "-v"
        else:
            cmd = "--version"

        stdout = ""

        if filepath.exists():
            stdout = self.run([filepath.as_posix(), cmd])

        if version not in stdout:

            if _filename:
                filepath = self.tmp_path / filename

            with urlopen(request) as response:
                with open(filepath, "wb") as file:
                    file.write(response.read())

            callback(filepath)

    def process_urls(self):
        for filename, data in self.github_api.data.items():
            url = data["url"]
            version = data["version"]
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            thread = Thread(
                target=self.download,
                args=(
                    request,
                    filename,
                    version,
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
ExecStart={Downloader.bin_path.as_posix()}/{GitHubAPI.filenames[-2]}

[Install]
WantedBy=multi-user.target"""
    install_commands = [
        "systemctl daemon-reload",
        f"systemctl enable --now {GitHubAPI.filenames[-2]}",
    ]
    uninstall_commands = [f"systemctl disable --now {GitHubAPI.filenames[-2]}", "rm {}"]
    paths = [
        Downloader.bin_path / filename
        for filename in GitHubAPI.filenames + Downloader.filenames
    ]

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true", default=False)
    args = parser.parse_args()

    installer = Installer()

    if args.uninstall:
        print("\x1b[36m" + "Removing VPN Manager" + "\x1b[39m")
        installer.uninstall()
    else:
        downloader = Downloader()

        print("Welcome to" + "\x1b[36m" + " VPN Manager!" + "\x1b[39m")
        print()
        print(
            "This will download and install the latest version of"
            + "\x1b[36m"
            + " vpnm,"
            + "\x1b[39m"
        )
        print(
            "an alternative CLI client for" + "\x1b[36m" + " VPN Manager." + "\x1b[39m"
        )
        print()
        print("It will add the `vpnm` command to system's bin directory, located at:")
        print()
        print("\x1b[36m" + downloader.bin_path.as_posix() + "\x1b[39m")
        print()
        print(
            "You can uninstall at any time by executing this script with the --uninstall option,"
        )
        print("and these changes will be reverted.")
        print()
        print("\x1b[36m" + "Retrieving dependencies..." + "\x1b[39m")
        print()

        downloader.process_urls()

        print("\x1b[36m" + "Installing VPN Manager..." + "\x1b[39m")
        print()

        installer.install()

        print("\x1b[36m" + "VPN Manager is installed now. Great!" + "\x1b[39m")
        print()
        print("You can test that everything is set up by executing:")
        print("`vpnm --help`")
