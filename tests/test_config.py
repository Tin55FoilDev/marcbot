"""Tests for MarcBot config loading."""

from pathlib import Path

import pytest

from marcbot.config import load_config
from marcbot.errors import MarcBotError


def write_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "marcbot.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_minimal_config(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        """
[app]
name = "MarcBot"
environment = "test"
""",
    )

    config = load_config(path)

    assert config.app.name == "MarcBot"
    assert config.app.environment == "test"
    assert config.telegram.enabled is False
    assert config.telegram.bot_token == ""
    assert config.telegram.allowed_chat_ids == ()


def test_load_telegram_disabled_config(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        """
[app]
name = "MarcBot"
environment = "test"

[telegram]
enabled = false
bot_token = ""
allowed_chat_ids = []
""",
    )

    config = load_config(path)

    assert config.telegram.enabled is False


def test_missing_config_file_raises_clean_error(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.toml"

    with pytest.raises(MarcBotError) as excinfo:
        load_config(missing_path)

    assert excinfo.value.code == "MBOT-CONFIG-001"


def test_invalid_toml_raises_clean_error(tmp_path: Path) -> None:
    path = write_config(tmp_path, "[app\n")

    with pytest.raises(MarcBotError) as excinfo:
        load_config(path)

    assert excinfo.value.code == "MBOT-CONFIG-002"


def test_missing_app_section_raises_clean_error(tmp_path: Path) -> None:
    path = write_config(tmp_path, "[telegram]\nenabled = false\n")

    with pytest.raises(MarcBotError) as excinfo:
        load_config(path)

    assert excinfo.value.code == "MBOT-CONFIG-005"


def test_telegram_enabled_requires_token(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        """
[app]
name = "MarcBot"
environment = "test"

[telegram]
enabled = true
bot_token = ""
""",
    )

    with pytest.raises(MarcBotError) as excinfo:
        load_config(path)

    assert excinfo.value.code == "MBOT-CONFIG-012"


def test_allowed_chat_ids_must_be_integers(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        """
[app]
name = "MarcBot"
environment = "test"

[telegram]
enabled = false
allowed_chat_ids = ["bad"]
""",
    )

    with pytest.raises(MarcBotError) as excinfo:
        load_config(path)

    assert excinfo.value.code == "MBOT-CONFIG-010"
