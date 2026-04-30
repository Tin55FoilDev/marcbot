"""Tests for MarcBot CLI behavior."""

from marcbot import __version__
from marcbot.cli import main


def test_version_command(capsys) -> None:
    result = main(["--version"])
    captured = capsys.readouterr()

    assert result == 0
    assert f"MarcBot {__version__}" in captured.out


def test_help_command(capsys) -> None:
    result = main([])
    captured = capsys.readouterr()

    assert result == 0
    assert "MarcBot personal automation CLI" in captured.out


def test_config_check_missing_file_returns_error(capsys, monkeypatch, tmp_path) -> None:
    missing_config = tmp_path / "missing.toml"

    import marcbot.cli as cli

    monkeypatch.setattr(cli, "DEFAULT_CONFIG_PATH", missing_config)

    result = main(["config-check"])
    captured = capsys.readouterr()

    assert result == 1
    assert "ERROR [MBOT-CONFIG-001]" in captured.err
