"""Tests for MarcBot CLI behavior."""

import logging

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
    test_log = tmp_path / "marcbot-test.log"

    import marcbot.cli as cli

    def configure_test_logging() -> None:
        logging.basicConfig(
            filename=test_log,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            force=True,
        )

    monkeypatch.setattr(cli, "DEFAULT_CONFIG_PATH", missing_config)
    monkeypatch.setattr(cli, "configure_logging", configure_test_logging)

    result = main(["config-check"])
    captured = capsys.readouterr()

    logging.shutdown()

    assert result == 1
    assert "ERROR [MBOT-CONFIG-001]" in captured.err
    assert test_log.is_file()
    assert str(missing_config) in test_log.read_text(encoding="utf-8")
