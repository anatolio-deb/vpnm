import subprocess
from typing import Iterable


class SystemdRunError(BaseException):
    pass


CMD = [
    "systemd-run",
    "--user",
    "--collect",
    "-p",
    "Restart=on-failure",
]


def run(command: Iterable) -> str:
    cmd = CMD.copy()
    cmd.extend(command)

    proc = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
    )

    if proc.returncode != 0:
        raise SystemdRunError(proc.stderr.decode())

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
    if "active" in proc.stdout.decode().split():
        return True
    return False


def stop(unit: str) -> None:
    subprocess.run(
        ["systemctl", "--user", "stop", unit],
        check=False,
        capture_output=True,
    )
