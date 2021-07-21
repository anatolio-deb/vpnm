from __future__ import annotations

import subprocess
import zipfile
from typing import Callable
from urllib.request import Request, urlopen

LINKS = [
    "https://raw.githubusercontent.com/v2fly/fhs-install-v2ray/master/install-release.sh",
    "https://github.com/xjasonlyu/tun2socks/releases/download/v2.2.0/tun2socks-linux-amd64.zip",
    "https://bin.equinox.io/c/VdrWdbjqyF/cloudflared-stable-linux-amd64.deb",
    "https://github.com/iochen/v2gen/releases/download/v2.0.1/v2gen_amd64_linux",
    "https://github.com/anatolio-deb/vpnmd/releases/download/latest/vpnmd",
    "https://github.com/anatolio-deb/vpnm/releases/download/latest/vpnm",
]
BIN_PATH = "/usr/local/bin"
UNIT_PATH = "/etc/systemd/system/vpnmd.service"
UNIT_CONTENT = """[Unit]
Description=VPN Manager daemon
After=network-online.target
Wants=network-online.target

[Service]
Restart=on-failure
ExecStart=/usr/local/bin/vpnmd

[Install]
WantedBy=multi-user.target"""

print(
    f"""# Welcome to VPN Manager!

This will download and install the latest version of vpnm,
an alternative CLI client for VPN Manager.

It will add the `vpnm` command to system's bin directory, located at:

{BIN_PATH}

You can uninstall at any time by executing this script with the --uninstall option,
and these changes will be reverted.
"""
)


def get_filename_from_link(link: str) -> str:
    return link[-link[::-1].find("/") :]


def get_filepath_from_filename(filename: str) -> str:
    if "." in filename:
        return f"/tmp/{filename}"
    return f"{BIN_PATH}/{filename}"


def get_post_download_action(link: str, filepath: str) -> Callable:
    if link is LINKS[0]:

        def post_download_action():
            subprocess.run(["bash", filepath], check=True)

    elif link is LINKS[1]:

        def post_download_action():
            with zipfile.ZipFile(filepath, "r") as zip_ref:
                zip_ref.extractall(BIN_PATH)

    elif link is LINKS[2]:

        def post_download_action():
            subprocess.run(
                ["dpkg", "-i", filepath],
                check=True,
            )

    else:

        def post_download_action():
            subprocess.run(["chmod", "+", "x", filepath], check=True)

    return post_download_action


def download(link: str, filepath: str) -> None:
    request = Request(link, headers={"User-Agent": "Mozilla/5.0"})

    with urlopen(request) as response:
        with open(filepath, "wb") as file:
            file.write(response.read())


def post_process():
    with open(UNIT_PATH, "w") as file:
        file.write(UNIT_CONTENT)

    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "--now", "vpnmd"], check=True)


def process_links():
    for link in LINKS:
        filename = get_filename_from_link(link)
        filepath = get_filepath_from_filename(filename)
        post_download_action = get_post_download_action(link, filepath)
        download(link, filepath)
        post_download_action()


def main(testing=False):
    try:
        process_links()

        if not testing:
            post_process()
    except (ConnectionError, subprocess.CalledProcessError) as ex:
        print(ex)
    else:
        print(
            """VPN Manager is installed now. Great!

            You can test that everything is set up by executing:

            `vpnm --help`
            """
        )


if __name__ == "__main__":
    main()
