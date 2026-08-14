"""
Shared authentication utilities for MiMinions CLI modules.

require_auth is centralised here so all CLI modules import from one place
instead of each defining their own copy.
"""

import functools

import click
from miminions.cli.auth import is_authenticated, is_public_access_enabled


def require_auth(f):
    """
    Decorator that gates a CLI command behind local sign-in.

    Behavior when the user is not authenticated:
      * If public access mode is enabled, the command runs anyway after
        printing a one-line warning (an explicit, opt-in bypass).
      * Otherwise the command is blocked: it prints a sign-in hint and
        returns without running.

    Usage:
        @some_group.command("my-command")
        @require_auth
        def my_command(...):
            ...
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            if is_public_access_enabled():
                click.echo("⚠️  Public access mode (not signed in).", err=True)
            else:
                click.echo("Please sign in first using 'miminions auth signin'", err=True)
                return None
        return f(*args, **kwargs)
    return wrapper
