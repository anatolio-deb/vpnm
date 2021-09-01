"""Control systemd transient units"""
import subprocess
from typing import List


def run(command: List[str]) -> str:
    proc = subprocess.run(
        [
            "systemd-run",
            "--user",
            "--collect",
            "-p",
            "Restart=on-failure",
        ]
        + command,
        check=True,
        capture_output=True,
    )

    return proc.stderr.decode().split(":")[1].strip()


def is_active(unit: str) -> bool:
    try:
        proc = subprocess.run(
            ["systemctl", "--user", "is-active", unit],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        return False
    if "active" in proc.stdout.decode():
        return True
    return False


def stop(unit: str) -> None:
    subprocess.run(
        ["systemctl", "--user", "stop", unit],
        check=False,
        capture_output=True,
    )
