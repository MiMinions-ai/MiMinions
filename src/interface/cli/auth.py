"""
Authentication commands for MiMinions CLI.
"""

import click
import os
import json
from pathlib import Path


def get_config_dir():
    """Get the configuration directory for MiMinions."""
    config_dir = Path.home() / ".miminions"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_auth_file():
    """Get the authentication file path."""
    return get_config_dir() / "auth.json"


def is_authenticated():
    """Check if user is authenticated."""
    auth_file = get_auth_file()
    return auth_file.exists() and auth_file.stat().st_size > 0


def save_auth_data(data):
    """Save authentication data."""
    auth_file = get_auth_file()
    with open(auth_file, "w") as f:
        json.dump(data, f, indent=2)


def load_auth_data():
    """Load authentication data."""
    auth_file = get_auth_file()
    if not auth_file.exists():
        return None
    
    with open(auth_file, "r") as f:
        return json.load(f)


def clear_auth_data():
    """Clear authentication data."""
    auth_file = get_auth_file()
    if auth_file.exists():
        auth_file.unlink()


@click.group()
def auth_cli():
    """Authentication commands."""
    pass


@auth_cli.command("signin")
@click.option("--username", prompt="Username", help="Your username")
@click.option("--password", prompt="Password", hide_input=True, help="Your password")
def signin(username, password):
    """Sign in to MiMinions."""
    # In a real implementation, this would authenticate with a server
    # For now, we'll just store the credentials locally
    
    if not username or not password:
        click.echo("Username and password are required.", err=True)
        return
    
    auth_data = {
        "username": username,
        "authenticated": True,
        "timestamp": click.get_current_context().meta.get("timestamp", "")
    }
    
    save_auth_data(auth_data)
    click.echo(f"Successfully signed in as {username}")


@auth_cli.command("signout")
def signout():
    """Sign out of MiMinions."""
    if not is_authenticated():
        click.echo("You are not currently signed in.")
        return
    
    auth_data = load_auth_data()
    username = auth_data.get("username", "unknown") if auth_data else "unknown"
    
    clear_auth_data()
    click.echo(f"Successfully signed out {username}")


@auth_cli.command("status")
def status():
    """Check authentication status."""
    if is_authenticated():
        auth_data = load_auth_data()
        username = auth_data.get("username", "unknown") if auth_data else "unknown"
        click.echo(f"Signed in as: {username}")
    else:
        click.echo("Not signed in")