"""
Authentication commands for MiMinions CLI.
"""

import click
import os
import json
import signal
import time
from pathlib import Path


def get_config_dir():
    """Get the configuration directory for MiMinions."""
    config_dir = Path.home() / ".miminions"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_config_file():
    """Get the configuration file path."""
    return get_config_dir() / "config.json"


def get_config():
    """Get the configuration settings."""
    config_file = get_config_file()
    if not config_file.exists():
        return {
            "public_access": False,
            "auth_timeout": 30
        }
    
    with open(config_file, "r") as f:
        return json.load(f)


def save_config(config):
    """Save configuration settings."""
    config_file = get_config_file()
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)


def get_auth_file():
    """Get the authentication file path."""
    return get_config_dir() / "auth.json"


def is_authenticated():
    """Check if user is authenticated."""
    auth_file = get_auth_file()
    return auth_file.exists() and auth_file.stat().st_size > 0


def is_public_access_enabled():
    """Check if public access mode is enabled."""
    config = get_config()
    return config.get("public_access", False)


def get_auth_timeout():
    """Get authentication timeout in seconds."""
    config = get_config()
    return config.get("auth_timeout", 30)


class AuthTimeoutError(Exception):
    """Exception raised when authentication times out."""
    pass


def timeout_handler(signum, frame):
    """Handle timeout signal."""
    raise AuthTimeoutError("Authentication operation timed out")


def with_timeout(func, timeout_seconds):
    """Execute function with timeout."""
    if os.name == 'nt':  # Windows doesn't support signal.alarm
        # For Windows, we'll use a simpler approach
        return func()
    
    # Set up timeout handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        result = func()
        signal.alarm(0)  # Cancel the alarm
        return result
    except AuthTimeoutError:
        raise
    finally:
        signal.signal(signal.SIGALRM, old_handler)


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
@click.option("--timeout", default=None, type=int, help="Authentication timeout in seconds")
def signin(username, password, timeout):
    """Sign in to MiMinions."""
    if not username or not password:
        click.echo("Username and password are required.", err=True)
        return
    
    # Use configured timeout if not specified
    if timeout is None:
        timeout = get_auth_timeout()
    
    def perform_auth():
        # In a real implementation, this would authenticate with a server
        # For now, we'll just store the credentials locally
        # Add a small delay to simulate network operation
        time.sleep(0.1)
        
        auth_data = {
            "username": username,
            "authenticated": True,
            "timestamp": str(int(time.time()))
        }
        
        save_auth_data(auth_data)
        return auth_data
    
    try:
        with_timeout(perform_auth, timeout)
        click.echo(f"Successfully signed in as {username}")
    except AuthTimeoutError:
        click.echo(f"Authentication timed out after {timeout} seconds. Please try again.", err=True)
    except Exception as e:
        click.echo(f"Authentication failed: {e}", err=True)


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
    
    # Show public access status
    if is_public_access_enabled():
        click.echo("Public access: enabled")
    else:
        click.echo("Public access: disabled")


@auth_cli.command("config")
@click.option("--public-access", type=bool, help="Enable/disable public access mode")
@click.option("--auth-timeout", type=int, help="Set authentication timeout in seconds")
def config_auth(public_access, auth_timeout):
    """Configure authentication settings."""
    config = get_config()
    
    if public_access is not None:
        config["public_access"] = public_access
        status_msg = "enabled" if public_access else "disabled"
        click.echo(f"Public access {status_msg}")
    
    if auth_timeout is not None:
        if auth_timeout < 5:
            click.echo("Timeout must be at least 5 seconds", err=True)
            return
        config["auth_timeout"] = auth_timeout
        click.echo(f"Authentication timeout set to {auth_timeout} seconds")
    
    save_config(config)
    
    if public_access is None and auth_timeout is None:
        # Show current config
        click.echo("Current authentication configuration:")
        click.echo(f"  Public access: {'enabled' if config.get('public_access', False) else 'disabled'}")
        click.echo(f"  Auth timeout: {config.get('auth_timeout', 30)} seconds")