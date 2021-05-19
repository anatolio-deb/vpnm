from threading import Thread

import click
import requests
import vpnmd_api
import web_api
from utils import animate


@click.group()
def cli():
    pass


@cli.command(help="Login into VPN Manager account.")
@click.option(
    "--email",
    prompt=web_api.get_prompt_desicion(),
    help="Registered email address."
)
@click.option(
    "--password",
    prompt=web_api.get_prompt_desicion(),
    hide_input=True,
    help="Password provided at registration."
)
def login(email: str, password: str):
    if web_api.get_prompt_desicion():
        try:
            response = web_api.get_token(email, password)
        except requests.exceptions.RequestException:
            click.secho("Can't connect to API", fg="red")
        else:
            if response.json()["msg"] != "ok":
                click.secho(response.json()["msg"], fg="yellow")
            else:
                secret = web_api.Secret()
                secret.data = response.json()["data"]["token"]
    if not web_api.get_prompt_desicion():
        click.secho("Logged in", fg="green")


@cli.command(help="Connect to the desired location.")
def connect():
    """Sends an IPC request to the VPNM daemon service"""
    if not web_api.get_prompt_desicion():
        connection = vpnmd_api.Connection()
        thread = Thread(target=connection.start)

        try:
            thread.start()
            animate(thread)
        except (
            requests.exceptions.RequestException,
            ConnectionRefusedError,
            ValueError,
            RuntimeError,
        ) as exception:
            if isinstance(exception, ConnectionRefusedError):
                click.echo("Is vpnm daemon running?")
                click.secho("Check it with 'systemctl status vpnmd'", fg="bright_black")
            else:
                connection.stop()
                if isinstance(exception, requests.exceptions.RequestException):
                    click.secho("Can't connect to API", fg="red")
                elif isinstance(exception, ValueError):
                    click.echo(exception)
                    click.secho(
                        "Consider changing your DNS or trying another node",
                        fg="bright_black",
                    )
                elif isinstance(exception, RuntimeError):
                    click.secho(exception, fg="red")
        else:
            address = web_api.check_ip()

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


@cli.command(help="Disconnect from the VPN service.")
def disconnect():
    connection = vpnmd_api.Connection()
    thread = Thread(target=connection.stop)
    try:
        thread.start()
        animate(thread)
    except ConnectionRefusedError:
        click.echo("Is vpnm daemon running?")
        click.secho("Check it with 'systemctl status vpnmd'", fg="bright_black")
    else:
        click.secho("Disconnected", fg="red")


@cli.command(help="Logout from you VPN Manager account.")
def logout():
    """Remove the web_api.PathService.secret"""
    if not web_api.get_prompt_desicion():
        web_api.Secret.file.unlink()
    click.secho("Logged out", fg="red")


if __name__ == "__main__":
    cli()
