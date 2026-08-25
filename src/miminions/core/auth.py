"""Placeholder authentication utilities for future account-backed features.

MiMinions is currently local-first and does not require sign-in for package or
CLI usage. The helpers remain so current auth commands keep working and future
advanced features can opt into real access control without changing call sites.
"""

from miminions.cli.auth import is_authenticated, is_public_access_enabled


def require_auth(f):
    """Compatibility decorator for commands that may require auth later.

    The current package does not require sign-in to use CLI commands, so this
    decorator intentionally leaves commands unblocked while preserving the
    call-site shape for future auth work.

    Usage:
        @some_group.command("my-command")
        @require_auth
        def my_command(...):
            ...
    """
    return f
