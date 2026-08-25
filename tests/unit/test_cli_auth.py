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

    target_config = {}
    current_config = get_config()
    public_access_enabled = is_public_access_enabled()
    auth_timeout = get_auth_timeout()
    assert current_config == target_config, f"expect result to be {target_config}, got {current_config}"
    assert public_access_enabled is False, f"expect is_public_access_enabled returns False, got {public_access_enabled}"
    assert auth_timeout == 30, f"expect result to be {30}, got {auth_timeout}"

    save_config({"public_access": True, "auth_timeout": 12})

    target_config = {"public_access": True, "auth_timeout": 12}
    current_config = get_config()
    public_access_enabled = is_public_access_enabled()
    auth_timeout = get_auth_timeout()
    assert current_config == target_config, f"expect result to be {target_config}, got {current_config}"
    assert public_access_enabled is True, f"expect is_public_access_enabled returns True, got {public_access_enabled}"
    assert auth_timeout == 12, f"expect result to be {12}, got {auth_timeout}"


def test_auth_config_command_shows_and_validates_settings(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.auth.get_config_dir", lambda: tmp_path)

    invalid = isolated_cli_runner.invoke(auth_cli, ["config", "--auth-timeout", "4"])
    assert invalid.exit_code == 0, f"expect cli exit code 0, got {invalid.exit_code} with output: {invalid.output}"
    target_value = "Timeout must be at least 5 seconds"
    assert target_value in invalid.output, f"expect {target_value} in invalid.output, got {invalid.output}"
    config_exists = (tmp_path / "config.json").exists()
    assert not config_exists, f"expect config command validation returns no config file created, got exists={config_exists}"

    updated = isolated_cli_runner.invoke(
        auth_cli,
        ["config", "--public-access", "true", "--auth-timeout", "9"],
    )
    assert updated.exit_code == 0, f"expect cli exit code 0, got {updated.exit_code} with output: {updated.output}"
    target_value = "Public access enabled"
    assert target_value in updated.output, f"expect {target_value} in updated.output, got {updated.output}"
    target_value = "Authentication timeout set to 9 seconds"
    assert target_value in updated.output, f"expect {target_value} in updated.output, got {updated.output}"

    shown = isolated_cli_runner.invoke(auth_cli, ["config"])
    assert shown.exit_code == 0, f"expect cli exit code 0, got {shown.exit_code} with output: {shown.output}"
    target_value = "Public access: enabled"
    assert target_value in shown.output, f"expect {target_value} in shown.output, got {shown.output}"
    target_value = "Auth timeout: 9 seconds"
    assert target_value in shown.output, f"expect {target_value} in shown.output, got {shown.output}"


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

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    target_value = "Successfully signed in as ada"
    assert target_value in result.output, f"expect {target_value} in result.output, got {result.output}"
    auth_data = load_auth_data()
    username = auth_data["username"]
    target_value = "ada"
    assert username == target_value, f"expect result to be {target_value}, got {username}"


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
    assert timed_out.exit_code == 0, f"expect cli exit code 0, got {timed_out.exit_code} with output: {timed_out.output}"
    target_value = "Authentication timed out after 6 seconds"
    assert target_value in timed_out.output, f"expect {target_value} in timed_out.output, got {timed_out.output}"

    def raise_error(func, timeout_seconds):
        raise RuntimeError("server down")

    monkeypatch.setattr("miminions.cli.auth.with_timeout", raise_error)
    failed = isolated_cli_runner.invoke(
        auth_cli,
        ["signin", "--username", "ada", "--password", "secret"],
    )
    assert failed.exit_code == 0, f"expect cli exit code 0, got {failed.exit_code} with output: {failed.output}"
    target_value = "Authentication failed: server down"
    assert target_value in failed.output, f"expect {target_value} in failed.output, got {failed.output}"


def test_status_includes_auth_and_public_access(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.auth.get_config_dir", lambda: tmp_path)
    (tmp_path / "auth.json").write_text(
        json.dumps({"username": "ada", "authenticated": True}),
        encoding="utf-8",
    )
    save_config({"public_access": True, "auth_timeout": 30})

    result = isolated_cli_runner.invoke(auth_cli, ["status"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    target_value = "Signed in as: ada"
    assert target_value in result.output, f"expect {target_value} in result.output, got {result.output}"
    target_value = "Public access: enabled"
    assert target_value in result.output, f"expect {target_value} in result.output, got {result.output}"


def test_with_timeout_windows_path_runs_function(monkeypatch):
    monkeypatch.setattr("miminions.cli.auth.os.name", "nt")

    result = with_timeout(lambda: "done", 1)
    target_value = "done"
    assert result == target_value, f"expect result to be {target_value}, got {result}"
