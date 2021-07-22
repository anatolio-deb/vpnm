import zipfile
from http.client import IncompleteRead
from subprocess import PIPE, STDOUT, Popen, TimeoutExpired
from threading import Thread
from typing import Callable
from urllib.request import Request, urlopen

LINKS = [
    "https://github.com/v2ray/dist/raw/master/v2ray-linux-64.zip",
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


def get_filename_from_link(link: str) -> str:
    return link[-link[::-1].find("/") :]


def get_filepath_from_filename(filename: str) -> str:
    if "." in filename:
        return f"/tmp/{filename}"
    return f"{BIN_PATH}/{filename}"


def get_post_download_action(filename: str, filepath: str) -> Callable:
    if ".zip" in filename:

        def post_download_action():
            with zipfile.ZipFile(filepath, "r") as zip_ref:
                zip_ref.extractall(BIN_PATH)

    elif ".deb" in filename:

        def post_download_action():
            with Popen(["dpkg", "-i", filepath], stdout=PIPE, stderr=STDOUT) as process:
                stdout = process.communicate()[0]

                if process.returncode != 0:
                    raise RuntimeError(stdout)

    else:

        def post_download_action():
            with Popen(
                ["chmod", "+x", filepath], stdout=PIPE, stderr=STDOUT
            ) as process:
                stdout = process.communicate()[0]

                if process.returncode != 0:
                    raise RuntimeError(stdout)

    return post_download_action


def download(link: str, filepath: str) -> None:
    request = Request(link, headers={"User-Agent": "Mozilla/5.0"})

    with urlopen(request) as response:
        with open(filepath, "wb") as file:
            file.write(response.read())


def post_process():
    with open(UNIT_PATH, "w") as file:
        file.write(UNIT_CONTENT)

    with Popen(["systemctl", "daemon-reload"], stdout=PIPE, stderr=STDOUT) as process:
        stdout = process.communicate()[0]

        if process.returncode != 0:
            raise RuntimeError(stdout)

    with Popen(
        ["systemctl", "enable", "--now", "vpnmd"], stdout=PIPE, stderr=STDOUT
    ) as process:
        stdout = process.communicate()[0]

        if process.returncode != 0:
            raise RuntimeError(stdout)


def downloader(link):
    filename = get_filename_from_link(link)
    filepath = get_filepath_from_filename(filename)
    post_download_action = get_post_download_action(filename, filepath)
    download(link, filepath)

    if ".zip" not in filename:
        post_download_action()


def process_links(testing: bool):
    if testing:
        links = LINKS[1:]
    else:
        links = LINKS

    threads = []

    for link in links:
        _thread = Thread(target=downloader, args=(link,))
        threads.append(_thread)
        _thread.start()

    for thread in threads:
        thread.join()


def main(testing=False):
    print(
        f"""Welcome to VPN Manager!

This will download and install the latest version of vpnm,
an alternative CLI client for VPN Manager.

It will add the `vpnm` command to system's bin directory, located at:

{BIN_PATH}

You can uninstall at any time by executing this script with the --uninstall option,
and these changes will be reverted."""
    )

    try:
        process_links(testing)
        post_process()
    except (ConnectionError, RuntimeError, TimeoutExpired, IncompleteRead) as ex:
        print(ex)
    else:
        print(
            """VPN Manager is installed now. Great!

You can test that everything is set up by executing:

`vpnm --help`"""
        )


if __name__ == "__main__":
    main()
