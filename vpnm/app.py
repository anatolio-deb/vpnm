import datetime
import re
from subprocess import CalledProcessError

import click
import requests
import vpnmd_api
import web_api
from utils import get_actual_address


@click.group()
def cli():
    """VPN Manager - secure internet access"""
    pass


@cli.command(help="Login into VPN Manager account")
@click.option(
    "--email",
    prompt=web_api.get_prompt_desicion(),
    help="Registered email address",
    # default="nikiforova693@gmail.com",
)
@click.option(
    "--password",
    prompt=web_api.get_prompt_desicion(),
    hide_input=True,
    help="Password provided at registration",
    # default="xaswug-syVryc-huvfy9",
)
def login(email: str, password: str):
    if web_api.get_prompt_desicion():
        auth = web_api.Auth()

        try:
            auth.set_secret(email, password)
        except requests.exceptions.RequestException:
            click.secho("Can't connect to API", fg="red")
        except ValueError as ex:
            click.secho(ex, fg="yellow")

    if not web_api.get_prompt_desicion():
        click.secho("Logged in", fg="green")


@cli.command(help="Get the current connection status")
def status():
    connection = vpnmd_api.Connection()

    if connection.is_active():
        click.secho(f"Connected to {connection.address}", fg="green")
    else:
        click.secho("Not connected", fg="red")


@cli.command(help="Get information on your account")
def account():
    if not web_api.get_prompt_desicion():
        auth = web_api.Auth()

        try:
            auth.set_account()
        except requests.RequestException:
            click.secho("Can't connect to API", fg="red")
        else:
            online = auth.account.get("online")
            limit = auth.account.get("limit")
            level = auth.account.get("account_level")
            balance = auth.account.get("balance")

            if level == 4:
                level = "VIP"
            elif level == 3:
                level = "Premium"
            elif level == 2:
                level = "Standart"

            pattern = re.compile(r"[\d.]*\d+")
            remaining = pattern.findall(auth.account.get("remaining_flow"))[0]
            total = auth.account.get("total_flow")
            expire_date = datetime.datetime.fromtimestamp(
                auth.account.get("expire_date")
            ).strftime("%Y-%m-%d, %H:%M:%S")

            click.echo(f"Current balance: {balance}")
            click.echo(f"Devices online: {online}/{limit}")
            click.echo(f"Expire date: {expire_date}")
            click.echo(f"Traffic left: {remaining}/{total}")


@cli.command(help="Connect to the desired location")
@click.option(
    "--best",
    "mode",
    help="Connect to the best server according to the latency",
    flag_value="-best",
    default="",
)
@click.option(
    "--random",
    "mode",
    help="Connect to the random server",
    flag_value="-random",
    default="",
)
@click.option("--ping", help="Wether to ping servers", is_flag=True, default=False)
def connect(mode, ping):
    """Sends an IPC request to the VPNM daemon service"""

    if not web_api.get_prompt_desicion():
        connection = vpnmd_api.Connection()

        try:
            connection.start(mode, ping)
        except (
            requests.exceptions.RequestException,
            ConnectionRefusedError,
            ValueError,
            OSError,
            CalledProcessError,
        ) as exception:
            if isinstance(exception, ConnectionRefusedError):
                click.echo("Is vpnm daemon running?")
                click.secho("Check it with 'systemctl status vpnmd'", fg="bright_black")
            elif isinstance(
                exception,
                (requests.exceptions.RequestException, OSError, CalledProcessError),
            ):
                click.secho("Can't connect to API", fg="red")
            else:
                connection.stop()

                if isinstance(exception, ValueError):
                    click.secho(
                        "Consider changing your DNS or trying another node",
                        fg="bright_black",
                    )
                click.secho(exception, fg="red")
        else:
            address = get_actual_address()

            click.secho(f"Connected to {address}", fg="green")

            if address != connection.address:
                click.secho(
                    f"However, {connection.address} is expected",
                    fg="bright_black",
                )
    else:
        click.echo("Are you logged in?")
        click.secho("Check it with 'vpnm login'", fg="bright_black")


@cli.command(help="Disconnect from the VPN service")
def disconnect():
    connection = vpnmd_api.Connection()

    try:
        if connection.is_active():
            connection.stop()
    except ConnectionRefusedError:
        click.echo("Is vpnm daemon running?")
        click.secho("Check it with 'systemctl status vpnmd'", fg="bright_black")
    finally:
        click.secho("Disconnected", fg="red")


@cli.command(help="Logout from your VPN Manager account")
def logout():
    """Remove the web_api.PathService.secret"""
    if not web_api.get_prompt_desicion():
        web_api.Secret.file.unlink()
    click.secho("Logged out", fg="red")


if __name__ == "__main__":
    cli()
