"""Tests for MarcBot Telegram bot helpers."""

import pytest

from marcbot.config import AppConfig, MarcBotConfig, TelegramConfig
from marcbot.errors import MarcBotError
from marcbot.telegram_bot import build_application, is_authorized_chat


def make_config(
    *,
    enabled: bool = True,
    token: str = "123456:test-token",
    allowed_chat_ids: tuple[int, ...] = (12345,),
) -> MarcBotConfig:
    return MarcBotConfig(
        app=AppConfig(name="MarcBot", environment="test"),
        telegram=TelegramConfig(
            enabled=enabled,
            bot_token=token,
            allowed_chat_ids=allowed_chat_ids,
        ),
    )


def test_is_authorized_chat_accepts_allowed_chat() -> None:
    assert is_authorized_chat(12345, (12345,)) is True


def test_is_authorized_chat_rejects_unknown_chat() -> None:
    assert is_authorized_chat(99999, (12345,)) is False


def test_is_authorized_chat_rejects_none() -> None:
    assert is_authorized_chat(None, (12345,)) is False


def test_is_authorized_chat_rejects_empty_allowlist() -> None:
    assert is_authorized_chat(12345, ()) is False


def test_build_application_rejects_disabled_telegram() -> None:
    with pytest.raises(MarcBotError) as excinfo:
        build_application(make_config(enabled=False))

    assert excinfo.value.code == "MBOT-TELEGRAM-001"


def test_build_application_rejects_empty_token() -> None:
    with pytest.raises(MarcBotError) as excinfo:
        build_application(make_config(token=""))

    assert excinfo.value.code == "MBOT-TELEGRAM-002"


def test_build_application_rejects_empty_allowlist() -> None:
    with pytest.raises(MarcBotError) as excinfo:
        build_application(make_config(allowed_chat_ids=()))

    assert excinfo.value.code == "MBOT-TELEGRAM-003"


def test_build_application_accepts_valid_config() -> None:
    application = build_application(make_config())

    assert application.bot_data["allowed_chat_ids"] == (12345,)
    assert application.bot_data["app_environment"] == "test"


def test_build_application_does_not_register_source_status_command() -> None:
    application = build_application(make_config())

    command_names = {
        command
        for handlers in application.handlers.values()
        for handler in handlers
        if hasattr(handler, "commands")
        for command in handler.commands
    }

    assert "source_status" not in command_names
    assert "report_status" in command_names
