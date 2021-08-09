import datetime
import re
from subprocess import CalledProcessError

import click
import requests
from requests.exceptions import HTTPError

from vpnm import __version__, vpnmd_api, web_api
from vpnm.utils import get_actual_address, get_location


@click.group()
@click.version_option(__version__, prog_name="vpnm")
# @click.pass_context
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
        except requests.exceptions.RequestException as ex:
            if isinstance(ex, HTTPError):
                click.secho(ex, fg="yellow")
            else:
                click.secho("Can't connect to API", fg="red")

    if not web_api.get_prompt_desicion():
        click.secho("Logged in", fg="green")


@cli.command(help="Get the current connection status")
def status():

    connection = vpnmd_api.Connection()

    try:
        if connection.is_active():
            click.secho(f"Connected to {connection.address}", fg="green")
        else:
            click.secho("Not connected", fg="red")
    except ConnectionRefusedError:
        click.echo("Is vpnm daemon running?")
        click.secho("Check it with 'systemctl status vpnmd'", fg="bright_black")


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
            days_left = str(
                datetime.datetime.fromtimestamp(auth.account.get("expire_date"))
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
@click.option(
    "--ping",
    help="Wether to ping servers before trying to connect",
    is_flag=True,
    default=False,
)
def connect(mode, ping):
    """Sends an IPC request to the VPNM daemon service"""

    if not web_api.get_prompt_desicion():

        connection = vpnmd_api.Connection()

        try:
            connection.start(mode, ping)
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
        except ValueError:
            click.secho(
                "Consider changing your DNS or trying another node",
                fg="yellow",
            )
        except OSError as ex:
            click.secho(ex, fg="red")
        # except KeyboardInterrupt:
        #     click.echo("Ending session properly, please wait...")
        #     connection.stop()
        else:
            address = get_actual_address()
            location = get_location(address)
            city = location.get("city")
            country = location.get("country")

            if city and country:
                location = ", " + city + ", " + country
            else:
                location = ""

            click.secho(f"Connected to {address}{location}", fg="green")

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
    else:
        click.secho("Disconnected", fg="red")


@cli.command(help="Logout from your VPN Manager account")
def logout():
    """Remove the web_api.PathService.secret"""
    if not web_api.get_prompt_desicion() and web_api.Secret.get_file().exists():
        web_api.Secret.get_file().unlink()
    click.secho("Logged out", fg="red")


if __name__ == "__main__":
    cli()
