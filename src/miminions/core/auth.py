"""
Shared authentication utilities for MiMinions CLI modules.

require_auth is centralised here so all CLI modules import from one place
instead of each defining their own copy.
"""

import click
from miminions.interface.cli.auth import is_authenticated, is_public_access_enabled


def require_auth(f):
    """
    Decorator that blocks a CLI command if the user is not authenticated.
    Allows through if public access mode is enabled.

    Usage:
        @some_group.command("my-command")
        @require_auth
        def my_command(...):
            ...
    """
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            if is_public_access_enabled():
                click.echo("⚠️  Public access mode.", err=True)
            else:
                click.echo("Please sign in first using 'miminions auth signin'", err=True)
                return
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper
