"""Configuration loading and validation for MarcBot."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from marcbot.errors import MarcBotError
from marcbot.paths import CONFIG_DIR

DEFAULT_CONFIG_PATH = CONFIG_DIR / "marcbot.toml"


@dataclass(frozen=True)
class AppConfig:
    """Application-level configuration."""

    name: str
    environment: str


@dataclass(frozen=True)
class TelegramConfig:
    """Telegram configuration placeholder.

    Telegram is not implemented yet. This structure exists so config behavior
    is stable before adding external integrations.
    """

    enabled: bool
    bot_token: str
    allowed_chat_ids: tuple[int, ...]


@dataclass(frozen=True)
class MarcBotConfig:
    """Full MarcBot configuration."""

    app: AppConfig
    telegram: TelegramConfig


def _read_toml_file(path: Path) -> dict[str, Any]:
    """Read a TOML file and return parsed data."""
    if not path.is_file():
        raise MarcBotError("MBOT-CONFIG-001", f"Missing config file: {path}")

    try:
        with path.open("rb") as file_obj:
            data = tomllib.load(file_obj)
    except tomllib.TOMLDecodeError as exc:
        raise MarcBotError("MBOT-CONFIG-002", f"Invalid TOML config file: {path}") from exc
    except OSError as exc:
        raise MarcBotError("MBOT-CONFIG-003", f"Unable to read config file: {path}") from exc

    if not isinstance(data, dict):
        raise MarcBotError("MBOT-CONFIG-004", f"Config root must be a table: {path}")

    return data


def _require_table(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a required table from parsed TOML."""
    value = data.get(key)
    if not isinstance(value, dict):
        raise MarcBotError("MBOT-CONFIG-005", f"Missing or invalid [{key}] config section")
    return value


def _require_nonempty_string(section: dict[str, Any], key: str, section_name: str) -> str:
    """Return a required non-empty string from a config section."""
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MarcBotError(
            "MBOT-CONFIG-006",
            f"Missing or invalid config value: {section_name}.{key}",
        )
    return value.strip()


def _optional_bool(section: dict[str, Any], key: str, default: bool) -> bool:
    """Return an optional boolean from a config section."""
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise MarcBotError("MBOT-CONFIG-007", f"Config value must be true/false: {key}")
    return value


def _optional_string(section: dict[str, Any], key: str, default: str = "") -> str:
    """Return an optional string from a config section."""
    value = section.get(key, default)
    if not isinstance(value, str):
        raise MarcBotError("MBOT-CONFIG-008", f"Config value must be a string: {key}")
    return value


def _optional_int_tuple(section: dict[str, Any], key: str) -> tuple[int, ...]:
    """Return an optional list of integers as a tuple."""
    value = section.get(key, [])
    if not isinstance(value, list):
        raise MarcBotError("MBOT-CONFIG-009", f"Config value must be a list: {key}")

    result: list[int] = []
    for item in value:
        if not isinstance(item, int):
            raise MarcBotError("MBOT-CONFIG-010", f"Config list must contain only integers: {key}")
        result.append(item)

    return tuple(result)


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> MarcBotConfig:
    """Load and validate MarcBot configuration."""
    data = _read_toml_file(path)

    app_section = _require_table(data, "app")
    telegram_section = data.get("telegram", {})
    if not isinstance(telegram_section, dict):
        raise MarcBotError("MBOT-CONFIG-011", "Invalid [telegram] config section")

    app = AppConfig(
        name=_require_nonempty_string(app_section, "name", "app"),
        environment=_require_nonempty_string(app_section, "environment", "app"),
    )

    telegram = TelegramConfig(
        enabled=_optional_bool(telegram_section, "enabled", False),
        bot_token=_optional_string(telegram_section, "bot_token", ""),
        allowed_chat_ids=_optional_int_tuple(telegram_section, "allowed_chat_ids"),
    )

    if telegram.enabled and not telegram.bot_token.strip():
        raise MarcBotError(
            "MBOT-CONFIG-012",
            "Telegram is enabled but telegram.bot_token is empty",
        )

    return MarcBotConfig(app=app, telegram=telegram)
