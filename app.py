"""A click framework console application"""
import datetime
import json
import re
from subprocess import CalledProcessError

import click
import requests
from requests.exceptions import HTTPError
from vpnmauth import VpnmApiClient

from vpnm import __version__, vpnmd_api, web_api
from vpnm.utils import SECRET, get_location, init


@click.group()
@click.version_option(__version__, prog_name="vpnm")
# @click.pass_context
def cli():
    """VPN Manager - secure internet access"""
    init()


@cli.command(help="Login into VPN Manager account")
@click.option(
    "--email", prompt=not web_api.is_authenticated(), help="Registered email address"
)
@click.option(
    "--password",
    prompt=not web_api.is_authenticated(),
    hide_input=True,
    help="Password provided at registration",
)
def login(email: str, password: str):
    if not web_api.is_authenticated():
        api_client = VpnmApiClient(email=email, password=password)
        print(api_client.api_url)

        try:
            response = api_client.login()
        except requests.exceptions.RequestException as ex:
            if isinstance(ex, HTTPError):
                click.secho(ex, fg="yellow")
            else:
                click.secho("Can't connect to API", fg="red")
        else:
            with open(SECRET, "w", encoding="utf-8") as file:
                json.dump(response["data"], file)

    if web_api.is_authenticated():
        click.secho("Logged in", fg="green")


@cli.command(help="Get the current connection status")
def status():
    try:
        if connection.is_active():
            location = get_location(connection.address)
            click.secho(f"Connected to {connection.address}{location}", fg="green")
        else:
            click.secho("Not connected", fg="red")
    except ConnectionRefusedError:
        click.echo("Is vpnm daemon running?")
        click.secho("Check it with 'systemctl status vpnmd'", fg="bright_black")


@cli.command(help="Get information on your account")
def account():
    if web_api.is_authenticated():
        with open(SECRET, "r", encoding="utf-8") as file:
            secret = json.load(file)

        api_client = VpnmApiClient(
            user_id=secret["user_id"],
            token=secret["token"],
        )

        try:
            response = api_client.account
        except requests.RequestException:
            click.secho("Can't connect to API", fg="red")
        else:
            online = response["data"]["online"]
            limit = response["data"]["limit"]
            level = response["data"]["account_level"]
            balance = response["data"]["balance"]

            if level == 4:
                level = "VIP"
            elif level == 3:
                level = "Premium"
            elif level == 2:
                level = "Standart"

            pattern = re.compile(r"[\d.]*\d+")
            remaining = pattern.findall(response["data"]["remaining_flow"])[0]
            total = response["data"]["total_flow"]
            days_left = str(
                datetime.datetime.fromtimestamp(response["data"]["expire_date"])
                - datetime.datetime.now()
            )

            click.echo(f"Current balance: {balance}")
            click.echo(f"Devices online: {online}/{limit}")
            click.echo(f"Days left: {days_left}")
            click.echo(f"Traffic left: {remaining}/{total}")
    else:
        click.echo("Are you logged in?")
        click.secho("Check it with 'vpnm login'", fg="bright_black")


@cli.command(help="Connect to the desired location")
@click.option(
    "--best",
    "mode",
    help="Connect to the best server according to the latency",
    flag_value="best",
    default="",
)
@click.option(
    "--random",
    "mode",
    help="Connect to the random server",
    flag_value="random",
    default="",
)
def connect(mode):
    """Sends an IPC request to the VPNM daemon service"""

    if web_api.is_authenticated():
        try:
            connection.start(mode)
        except ConnectionRefusedError:
            click.echo("Is vpnm daemon running?")
            click.secho("Check it with 'systemctl status vpnmd'", fg="bright_black")
        except requests.exceptions.RequestException as ex:
            if isinstance(ex, HTTPError):
                click.secho(ex, fg="yellow")
            else:
                click.secho("Can't connect to API", fg="red")
        except CalledProcessError as ex:
            click.secho(ex.stderr.decode(), fg="red")
        except OSError as ex:
            click.secho(ex, fg="red")
        except KeyboardInterrupt:

            while True:
                click.echo("Ending the session properly, please wait...")

                try:
                    connection.stop()
                except KeyboardInterrupt:
                    click.clear()
                else:
                    break
        else:
            if connection.is_active():
                location = get_location(connection.address)
                click.secho(f"Connected to {connection.address}{location}", fg="green")
            else:
                click.secho("Not connected", fg="red")
    else:
        click.echo("Are you logged in?")
        click.secho("Check it with 'vpnm login'", fg="bright_black")


@cli.command(help="Disconnect from the VPN service")
@click.option(
    "--force",
    help="Disconnect without checking connecton status",
    is_flag=True,
    default=False,
)
def disconnect(force: bool):
    try:
        if connection.is_active() or force:
            connection.stop()
    except ConnectionRefusedError:
        click.echo("Is vpnm daemon running?")
        click.secho("Check it with 'systemctl status vpnmd'", fg="bright_black")
    else:
        click.secho("Disconnected", fg="red")


@cli.command(help="Logout from your VPN Manager account")
def logout():
    """Remove the web_api.PathService.secret"""

    if web_api.is_authenticated():
        SECRET.unlink()
    click.secho("Logged out", fg="red")


if __name__ == "__main__":
    connection = vpnmd_api.Connection()
    cli()
