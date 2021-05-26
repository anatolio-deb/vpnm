import datetime
import re

import click
import requests
import vpnmd_api
import web_api
from requests.exceptions import RequestException
from utils import check_ip


@click.group()
def cli():
    """VPN Manager - secure internet access"""
    pass


@cli.command(help="Login into VPN Manager account")
@click.option(
    "--email",
    prompt=web_api.get_prompt_desicion(),
    help="Registered email address",
    default="nikiforova693@gmail.com",
)
@click.option(
    "--password",
    prompt=web_api.get_prompt_desicion(),
    hide_input=True,
    help="Password provided at registration",
    default="xaswug-syVryc-huvfy9",
)
def login(email: str, password: str):
    if web_api.get_prompt_desicion():
        auth = web_api.Auth()

        try:
            auth.get_token(email, password)
        except requests.exceptions.RequestException:
            click.secho("Can't connect to API", fg="red")
        except ValueError as ex:
            click.secho(ex, fg="yellow")

    if not web_api.get_prompt_desicion():
        click.secho("Logged in", fg="green")


@cli.command(help="Get the current connection status")
def status():
    connection = vpnmd_api.Connection()

    try:
        connection.status()

        if connection.node:
            connection.node.set_address()
            address = check_ip()
        else:
            raise ValueError
    except (requests.exceptions.RequestException, ValueError, OSError):
        click.secho("Not connected", fg="red")
    else:
        if address != connection.node.address:
            click.secho(
                "Your IP address is {}, however, {} is "
                "expected.".format(address, connection.node.address),
                fg="green",
            )
        else:
            click.secho(
                "Your IP address is {}.".format(connection.node.address), fg="green"
            )
        click.secho("Connected to {}.".format(connection.node.name), fg="green")


@cli.command(help="Get information on your account")
def account():
    if not web_api.get_prompt_desicion():
        auth = web_api.Auth()

        try:
            auth.get_account()
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
def connect():
    """Sends an IPC request to the VPNM daemon service"""
    if not web_api.get_prompt_desicion():
        connection = vpnmd_api.Connection()

        try:
            connection.start()
        except (
            requests.exceptions.RequestException,
            ConnectionRefusedError,
            ValueError,
            OSError,
        ) as exception:
            if isinstance(exception, ConnectionRefusedError):
                click.echo("Is vpnm daemon running?")
                click.secho("Check it with 'systemctl status vpnmd'", fg="bright_black")
            elif isinstance(exception, (requests.exceptions.RequestException, OSError)):
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
            address = check_ip()

            if address != connection.node.address:
                click.secho(
                    "Your IP address is {}, however, {} is "
                    "expected.".format(address, connection.node.address),
                    fg="green",
                )
            else:
                click.secho(
                    "Your IP address is {}.".format(connection.node.address), fg="green"
                )
            click.secho("Connected to {}.".format(connection.node.name), fg="green")
    else:
        click.echo("Are you logged in?")
        click.secho("Check it with 'vpnm login'", fg="bright_black")


@cli.command(help="Disconnect from the VPN service")
def disconnect():
    connection = vpnmd_api.Connection()

    try:
        connection.status()

        if connection.node:
            connection.stop()
    except (FileNotFoundError, RequestException, ConnectionRefusedError) as ex:
        if isinstance(ex, ConnectionRefusedError):
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
