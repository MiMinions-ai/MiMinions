import json

from miminions.cli.auth import (
    AuthTimeoutError,
    auth_cli,
    get_auth_timeout,
    get_config,
    is_public_access_enabled,
    load_auth_data,
    save_config,
    with_timeout,
)


def test_config_defaults_and_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.auth.get_config_dir", lambda: tmp_path)

    assert get_config() == {"public_access": False, "auth_timeout": 30}
    assert is_public_access_enabled() is False
    assert get_auth_timeout() == 30

    save_config({"public_access": True, "auth_timeout": 12})

    assert get_config() == {"public_access": True, "auth_timeout": 12}
    assert is_public_access_enabled() is True
    assert get_auth_timeout() == 12


def test_auth_config_command_shows_and_validates_settings(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.auth.get_config_dir", lambda: tmp_path)

    invalid = isolated_cli_runner.invoke(auth_cli, ["config", "--auth-timeout", "4"])
    assert invalid.exit_code == 0
    assert "Timeout must be at least 5 seconds" in invalid.output
    assert not (tmp_path / "config.json").exists()

    updated = isolated_cli_runner.invoke(
        auth_cli,
        ["config", "--public-access", "true", "--auth-timeout", "9"],
    )
    assert updated.exit_code == 0
    assert "Public access enabled" in updated.output
    assert "Authentication timeout set to 9 seconds" in updated.output

    shown = isolated_cli_runner.invoke(auth_cli, ["config"])
    assert shown.exit_code == 0
    assert "Public access: enabled" in shown.output
    assert "Auth timeout: 9 seconds" in shown.output


def test_signin_uses_configured_timeout_and_persists_auth(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.cli.auth.get_config_dir", lambda: tmp_path)
    (tmp_path / "config.json").write_text(
        json.dumps({"public_access": False, "auth_timeout": 8}),
        encoding="utf-8",
    )
    monkeypatch.setattr("miminions.cli.auth.time.sleep", lambda _seconds: None)

    result = isolated_cli_runner.invoke(
        auth_cli,
        ["signin", "--username", "ada", "--password", "secret"],
    )

    assert result.exit_code == 0
    assert "Successfully signed in as ada" in result.output
    assert load_auth_data()["username"] == "ada"


def test_signin_timeout_and_unexpected_error_are_reported(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.cli.auth.get_config_dir", lambda: tmp_path)

    def raise_timeout(func, timeout_seconds):
        raise AuthTimeoutError("slow")

    monkeypatch.setattr("miminions.cli.auth.with_timeout", raise_timeout)
    timed_out = isolated_cli_runner.invoke(
        auth_cli,
        ["signin", "--username", "ada", "--password", "secret", "--timeout", "6"],
    )
    assert timed_out.exit_code == 0
    assert "Authentication timed out after 6 seconds" in timed_out.output

    def raise_error(func, timeout_seconds):
        raise RuntimeError("server down")

    monkeypatch.setattr("miminions.cli.auth.with_timeout", raise_error)
    failed = isolated_cli_runner.invoke(
        auth_cli,
        ["signin", "--username", "ada", "--password", "secret"],
    )
    assert failed.exit_code == 0
    assert "Authentication failed: server down" in failed.output


def test_status_includes_auth_and_public_access(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.auth.get_config_dir", lambda: tmp_path)
    (tmp_path / "auth.json").write_text(
        json.dumps({"username": "ada", "authenticated": True}),
        encoding="utf-8",
    )
    save_config({"public_access": True, "auth_timeout": 30})

    result = isolated_cli_runner.invoke(auth_cli, ["status"])

    assert result.exit_code == 0
    assert "Signed in as: ada" in result.output
    assert "Public access: enabled" in result.output


def test_with_timeout_windows_path_runs_function(monkeypatch):
    monkeypatch.setattr("miminions.cli.auth.os.name", "nt")

    assert with_timeout(lambda: "done", 1) == "done"
