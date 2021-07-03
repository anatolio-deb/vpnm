import subprocess
import zipfile
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
SERVICE = """[Unit]
Description=VPN Manager daemon
After=network-online.target
Wants=network-online.target

[Service]
Restart=on-failure
ExecStart=/usr/local/bin/vpnmd

[Install]
WantedBy=multi-user.target"""

for link in LINKS:
    filename = link[-link[::-1].find("/") :]

    if "." in filename:
        filepath = f"/tmp/{filename}"
    else:
        filepath = f"{BIN_PATH}/{filename}"

    request = Request(link, headers={"User-Agent": "Mozilla/5.0"})

    with urlopen(request) as response:
        with open(filepath, "wb") as file:
            file.write(response.read())

    if link is LINKS[0]:
        subprocess.run(["bash", filepath], check=True)
    elif link is LINKS[1]:
        with zipfile.ZipFile(filepath, "r") as zip_ref:
            zip_ref.extractall(BIN_PATH)
    elif link is LINKS[2]:
        subprocess.run(
            ["dpkg", "-i", filepath],
            check=True,
        )
    else:
        subprocess.run(["chmod", "+", "x", filepath], check=True)

with open("/etc/systemd/system/vpnmd.service", "w") as file:
    file.write(SERVICE)

subprocess.run(["systemctl", "daemon-reload"], check=True)
subprocess.run(["systemctl", "enable", "--now", "vpnmd"], check=True)
subprocess.run(["vpnm"], check=True)

