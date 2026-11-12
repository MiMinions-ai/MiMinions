"""Regression tests for https://github.com/MiMinions-ai/MiMinions/issues/83."""

from __future__ import annotations

import sys
import time
import pytest

from click.testing import CliRunner


@pytest.fixture(autouse=True)
def restore_imported_modules():
    """Fresh-import assertions must not invalidate modules collected by later tests."""
    previous = {name: module for name, module in sys.modules.items() if name == "miminions" or name.startswith("miminions.")}
    yield
    for name in list(sys.modules):
        if (name == "miminions" or name.startswith("miminions.")) and name not in previous:
            sys.modules.pop(name, None)
    sys.modules.update(previous)
    for name, module in previous.items():
        parent_name, _, child = name.rpartition(".")
        if parent_name in previous:
            setattr(previous[parent_name], child, module)


def _fresh_cli():
    """Reload main so LazyGroup caches from prior tests do not leak."""
    for name in list(sys.modules):
        if name == "miminions.interface.cli.main" or name.startswith("miminions.interface.cli.main."):
            sys.modules.pop(name, None)
    from miminions.interface.cli import main as main_mod

    return main_mod.cli, main_mod


def test_help_skips_bootstrap_and_heavy_imports():
    """`--help` must not import agent/chat/gateway/bootstrap."""
    doomed = [
        name
        for name in list(sys.modules)
        if name in {
            "miminions.interface.cli.main",
            "miminions.interface.cli.management.agent",
            "miminions.interface.cli.operations.chat",
            "miminions.interface.cli.daemon",
            "miminions.interface.cli.operations.execution",
            "miminions.interface.cli.operations.prompt",
            "miminions.interface.cli.management.tool",
            "miminions.interface.bootstrap",
        }
        or name.startswith("miminions.interface.cli.management.agent.")
        or name.startswith("miminions.interface.cli.operations.chat.")
        or name.startswith("miminions.interface.cli.daemon.")
        or name.startswith("miminions.interface.cli.management.tool.")
    ]
    for name in doomed:
        sys.modules.pop(name, None)

    cli, _ = _fresh_cli()
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0, result.output
    assert "MiMinions CLI" in result.output
    assert "auth" in result.output
    assert "agent" in result.output
    assert "tool" in result.output
    assert "\n  execution " not in result.output
    # Static short helps (prove we did not import auth_cli docstring path for listing).
    assert "Create and manage agents." in result.output

    assert "miminions.interface.cli.management.agent" not in sys.modules
    assert "miminions.interface.cli.operations.chat" not in sys.modules
    assert "miminions.interface.cli.daemon" not in sys.modules
    assert "miminions.interface.cli.management.tool" not in sys.modules
    assert "miminions.interface.bootstrap" not in sys.modules


def test_help_completes_quickly_after_import():
    """Once the root module is imported, help should be near-instant."""
    cli, _ = _fresh_cli()
    runner = CliRunner()
    start = time.perf_counter()
    result = runner.invoke(cli, ["--help"])
    elapsed = time.perf_counter() - start
    assert result.exit_code == 0
    # Warm help must stay well under the 3–10s regression reported in #83.
    assert elapsed < 1.0, f"--help took {elapsed:.3f}s"


def test_lazy_subcommand_resolves_auth():
    """Resolving a light command still works after lazy registration."""
    from unittest.mock import patch

    cli, main_mod = _fresh_cli()
    runner = CliRunner()
    with patch.object(main_mod, "_maybe_bootstrap"):
        result = runner.invoke(cli, ["auth", "--help"])
    assert result.exit_code == 0
    assert "signin" in result.output or "Authentication" in result.output or "auth" in result.output.lower()


def test_all_lazy_commands_resolve():
    cli, main_mod = _fresh_cli()
    ctx = cli.make_context("miminions", [], resilient_parsing=True)
    for name, _, _, _ in main_mod._LAZY_COMMANDS:
        command = cli.get_command(ctx, name)
        assert command is not None, f"Could not load {name}"


def test_lazy_group_lists_all_commands():
    cli, _ = _fresh_cli()
    # Avoid no_args_is_help SystemExit by building a context that is not parsed.
    ctx = cli.make_context("miminions", ["--help"], resilient_parsing=True)
    names = cli.list_commands(ctx)
    for expected in ("auth", "agent", "tool", "task", "chat", "gateway", "prompt"):
        assert expected in names
    assert "execution" not in names
    assert "workflow" not in names


def test_version_reports_local_project_release():
    cli, _ = _fresh_cli()
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0, result.output
    assert "0.4.1" in result.output, result.output
