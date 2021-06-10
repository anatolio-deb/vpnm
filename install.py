import subprocess
import zipfile
from urllib.request import Request, urlopen

LINKS = {
    "https://raw.githubusercontent.com/v2fly/fhs-install-v2ray/master/install-release.sh": "install-release.sh",
    "https://github.com/iochen/v2gen/releases/download/v2.0.1/v2gen_amd64_linux": "v2gen_amd64_linux",
    "https://github.com/xjasonlyu/tun2socks/releases/download/v2.2.0/tun2socks-linux-amd64.zip": "tun2socks-linux-amd64.zip",
    "https://bin.equinox.io/c/VdrWdbjqyF/cloudflared-stable-linux-amd64.deb": "cloudflared-stable-linux-amd64.deb",
    "https://github.com/anatolio-deb/vpnmd/releases/download/latest/vpnmd": "vpnmd",
    "https://github.com/anatolio-deb/vpnmd/blob/main/vpnmd.service": "vpnmd.service",
    "https://github.com/anatolio-deb/vpnm/releases/download/latest/vpnm": "vpnm",
}
BIN_PATH = "/usr/local/bin"
DPATH = "/var/local/bin"
SVC_PATH = "/etc/systemd/system"

for link, filename in LINKS.items():
    if filename in [
        "install-release.sh",
        "tun2socks-linux-amd64.zip",
        "cloudflared-stable-linux-amd64.deb",
    ]:
        filepath = f"/tmp/{filename}"

        if filename == "tun2socks-linux-amd64.zip":

            def post_dl_act():
                with zipfile.ZipFile("/tmp/tun2socks-linux-amd64.zip", "r") as zip_ref:
                    zip_ref.extractall(BIN_PATH)

        elif filename == "cloudflared-stable-linux-amd64.deb":

            def post_dl_act():
                subprocess.run(
                    ["dpkg", "-i", "/tmp/cloudflared-stable-linux-amd64.deb"],
                    check=True,
                )

        else:

            def post_dl_act():
                subprocess.run(["bash", "/tmp/install-release.sh"], check=True)

    elif filename == "vpnmd":
        filepath = f"{DPATH}/{filename}"
    elif filename == "vpnmd.service":
        filepath = f"{SVC_PATH}/{filename}"
    else:
        filepath = f"{BIN_PATH}/{filename}"

    print(f"Downloading {filename} from {link} to {filepath}")

    request = Request(link, headers={"User-Agent": "Mozilla/5.0"})

    with urlopen(request) as response:
        with open(filepath, "wb") as file:
            file.write(response.read())

    if filename == "install-release.sh":
        print(f"Installing v2ray from {filepath}")
    elif filename == "tun2socks-linux-amd64.zip":
        print(f"Extracting {filepath} to {BIN_PATH}")
    else:
        print(f"Downloaded {filepath}")

    if filename in [
        "install-release.sh",
        "tun2socks-linux-amd64.zip",
        "cloudflared-stable-linux-amd64.deb",
    ]:
        post_dl_act()

subprocess.run(["systemctl", "daemon-reload"], check=True)
subprocess.run(["systemctl", "enable", "--now", "vpnmd"], check=True)
subprocess.run(["vpnm"], check=True)
