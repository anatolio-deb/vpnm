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
        self.set_data()

    @staticmethod
    def get_api_request_urls() -> list:
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
    def get_json_response(api_request_url: str) -> dict:
        request = Request(api_request_url, headers={"User-Agent": "Mozilla/5.0"})

        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def set_data(self):
        for url in self.get_api_request_urls():
            response = self.get_json_response(url)

            for asset in response["assets"]:
                if asset["name"] in self.filenames:
                    self.data[asset["name"]] = {
                        "url": asset["browser_download_url"],
                        "version": response["tag_name"],
                    }


class Downloader:
    github_api = GitHubAPI()
    bin_path = Path("/usr/local/bin")
    tmp_path = Path("/tmp")
    threads: list = []
    members = ["tun2socks-linux-amd64", "v2ray", "geoip.dat", "geosite.dat"]

    @staticmethod
    def run(command: list):
        """Run a shell command"""
        with Popen(command, stdout=PIPE, stderr=STDOUT) as process:
            stdout = process.communicate()[0]

            if process.returncode != 0:
                raise SubprocessError(stdout.decode())

        return stdout.decode()

    def unzip(self, filepath: Path, member: str):
        """Extract the whole zip archive or an exact file from it.

        Args:
            filepath (str): The location of a zip file
            member (str, optional): The exact file to extract. Defaults to None.
        """

        with zipfile.ZipFile(filepath, "r") as zip_ref:
            for _member in zip_ref.infolist():
                if _member.filename == member:
                    zip_ref.extract(_member, self.bin_path)

    def get_members(self, filename: str) -> list:
        if filename == GitHubAPI.filenames[0]:
            return self.members[:1]

        if filename == GitHubAPI.filenames[1]:
            return self.members[1:]

        return []

    def get_local_version(self, filepath: Path, cmd: str = "--version") -> str:
        stdout = ""

        if filepath.exists():

            if filepath is self.bin_path / GitHubAPI.filenames[3]:
                cmd = "-v"

            stdout = self.run([filepath.as_posix(), cmd])

        return stdout

    def download(self, request: Request, filename: str, version: str):
        members = self.get_members(filename)

        if members:
            filepath = self.bin_path / members[0]
        else:
            filepath = self.bin_path / filename

        local_version = self.get_local_version(filepath)

        if version not in local_version:
            if members:
                filepath = self.tmp_path / filename

            with urlopen(request) as response:
                with open(filepath, "wb") as file:
                    file.write(response.read())

            def callback(filepath: Path, members: list, flag: str = "x") -> None:
                _filepath = filepath
                remember = ""

                for member in members:
                    self.unzip(filepath, member)

                    if member in self.members[2:]:
                        flag = "r"

                    remember = member
                    break

                if remember:
                    _filepath = self.bin_path / remember
                    members.remove(remember)

                self.run(["chmod", f"ugo+{flag}", _filepath.as_posix()])

                if members:
                    callback(filepath, members)

            callback(filepath, members)

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
After=network-online.member
Wants=network-online.member

[Service]
Restart=on-failure
ExecStart={Downloader.bin_path.as_posix()}/{GitHubAPI.filenames[-2]}

[Install]
WantedBy=multi-user.member"""
    install_commands = [
        "systemctl daemon-reload",
        f"systemctl enable --now {GitHubAPI.filenames[-2]}",
    ]
    uninstall_commands = [f"systemctl disable --now {GitHubAPI.filenames[-2]}", "rm {}"]
    paths = [
        Downloader.bin_path / filename
        for filename in GitHubAPI.filenames[2:] + Downloader.members
    ]

    def __init__(self, verbosity: str) -> None:
        self.verbosity = verbosity

    def install(self):
        with open(self.unit_path, "w") as file:
            file.write(self.unit_content)

        for command in self.install_commands:
            try:
                stdout = Downloader.run(command.split())
            except SubprocessError as ex:
                if self.verbosity == "error":
                    print(ex)
            else:
                if self.verbosity == "info":
                    print(stdout)

    def uninstall(self):
        for command in self.uninstall_commands:
            if command is self.uninstall_commands[0]:
                try:
                    stdout = Downloader.run(command.split())
                except SubprocessError as ex:
                    if self.verbosity == "error":
                        print(ex)
                else:
                    if self.verbosity == "info":
                        print(stdout)
            else:
                self.paths.append(self.unit_path)

                for path in self.paths:
                    if path.exists() and path.is_file():
                        try:
                            stdout = Downloader.run(
                                command.format(path.as_posix()).split()
                            )
                        except SubprocessError as ex:
                            if self.verbosity == "error":
                                print(ex)
                        else:
                            if self.verbosity == "info":
                                print(stdout)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true", default=False)
    parser.add_argument(
        "--verbosity", choices=["info", "error", "none"], default="none"
    )
    args = parser.parse_args()

    installer = Installer(args.verbosity)

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
            "You can uninstall at any time by executing this script with the "
            " --uninstall option,"
        )
        print("and these changes will be reverted.")
        print()
        print("\x1b[36m" + "Retrieving dependencies..." + "\x1b[39m")
        print()

        downloader.process_urls()

        print("Installing" + "\x1b[36m" + "VPN Manager" + "\x1b[39m" + "...")
        print()

        installer.install()

        print("\x1b[36m" + "VPN Manager" + "\x1b[39m" + "is installed now. Great!")
        print()
        print("You can test that everything is set up by executing:")
        print("`vpnm --help`")
