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
    assert "send_source_artifact" in command_names
    assert "llm_status" in command_names


def test_send_source_artifact_sends_resolved_document(monkeypatch, tmp_path) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    artifact = tmp_path / "source-monitor-2026-05-08-113613.md"
    artifact.write_text("report", encoding="utf-8")

    sent_documents = []

    class FakeMessage:
        async def reply_document(self, **kwargs):
            sent_documents.append(kwargs)

        async def reply_text(self, text):
            raise AssertionError(f"unexpected reply_text: {text}")

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        args=["ai", "report:2026-05-08-113613"],
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    monkeypatch.setattr(
        telegram_bot,
        "resolve_source_monitor_artifact",
        lambda artifact_id, project_name: artifact,
    )

    asyncio.run(telegram_bot.send_source_artifact_command(update, context))

    assert sent_documents == [
        {
            "document": artifact,
            "filename": artifact.name,
            "caption": (
                "🤖 MarcBot source monitor artifact\n"
                "Project: ai\n"
                "Artifact ID: report:2026-05-08-113613"
            ),
        }
    ]


def test_send_source_artifact_reports_missing_artifact(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    replies = []

    class FakeMessage:
        async def reply_document(self, **kwargs):
            raise AssertionError(f"unexpected reply_document: {kwargs}")

        async def reply_text(self, text):
            replies.append(text)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        args=["ai", "report:1999-01-01-000000"],
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    monkeypatch.setattr(
        telegram_bot,
        "resolve_source_monitor_artifact",
        lambda artifact_id, project_name: None,
    )

    asyncio.run(telegram_bot.send_source_artifact_command(update, context))

    assert replies == [
        "🤖 MarcBot source monitor artifact\n"
        "Project: ai\n"
        "Artifact ID: report:1999-01-01-000000\n"
        "Status: not found"
    ]


def test_chat_commands_are_registered() -> None:
    application = build_application(make_config())
    command_names = {
        command
        for handlers in application.handlers.values()
        for handler in handlers
        if hasattr(handler, "commands")
        for command in handler.commands
    }

    assert "chat_start" in command_names
    assert "chat_status" in command_names
    assert "chat_clear" in command_names
    assert "chat_stop" in command_names


def test_chat_status_reports_inactive(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    replies = []

    class FakeMessage:
        async def reply_text(self, text):
            replies.append(text)

    store = telegram_bot.ChatSessionStore()
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        args=[],
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_status_command(update, context))

    assert replies == [
        "MarcBot chat status\nStatus: inactive\nProvider contact: no"
    ]


def test_chat_start_rejects_unknown_profile(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    replies = []

    class FakeMessage:
        async def reply_text(self, text):
            replies.append(text)

    store = telegram_bot.ChatSessionStore()
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)
    monkeypatch.setattr(
        telegram_bot,
        "load_llm_config",
        lambda: SimpleNamespace(profiles={}),
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        args=["missing"],
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_start_command(update, context))

    assert replies == ["Unknown chat profile: missing"]
    assert store.get(chat_id=123) is None


def test_chat_start_rejects_non_chat_profile(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    replies = []

    class FakeMessage:
        async def reply_text(self, text):
            replies.append(text)

    store = telegram_bot.ChatSessionStore()
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)
    monkeypatch.setattr(
        telegram_bot,
        "load_llm_config",
        lambda: SimpleNamespace(
            profiles={
                "local_fast": SimpleNamespace(
                    name="local_fast",
                    chat_enabled=False,
                )
            }
        ),
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        args=["local_fast"],
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_start_command(update, context))

    assert replies == ["Profile is not approved for chat: local_fast"]
    assert store.get(chat_id=123) is None


def test_chat_start_accepts_chat_enabled_profile(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    replies = []

    class FakeMessage:
        async def reply_text(self, text):
            replies.append(text)

    store = telegram_bot.ChatSessionStore()
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)
    monkeypatch.setattr(
        telegram_bot,
        "load_llm_config",
        lambda: SimpleNamespace(
            profiles={
                "local_fast": SimpleNamespace(
                    name="local_fast",
                    chat_enabled=True,
                )
            }
        ),
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        args=["local_fast"],
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_start_command(update, context))

    assert replies == [
        "MarcBot chat started.\n"
        "Profile: local_fast\n"
        "Provider contact: not yet; future chat text will contact "
        "the configured model provider."
    ]
    session = store.get(chat_id=123)
    assert session is not None
    assert session.profile_name == "local_fast"


def test_chat_clear_and_stop(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    clear_replies = []
    stop_replies = []

    class ClearMessage:
        async def reply_text(self, text):
            clear_replies.append(text)

    class StopMessage:
        async def reply_text(self, text):
            stop_replies.append(text)

    store = telegram_bot.ChatSessionStore()
    store.start(chat_id=123, profile_name="local_fast")
    store.append_message(chat_id=123, role="user", content="hello")
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)

    clear_update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=ClearMessage(),
    )
    clear_context = SimpleNamespace(
        args=[],
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )
    asyncio.run(telegram_bot.chat_clear_command(clear_update, clear_context))

    assert clear_replies == ["MarcBot chat history cleared."]
    session = store.get(chat_id=123)
    assert session is not None
    assert session.history == []

    stop_update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=StopMessage(),
    )
    stop_context = SimpleNamespace(
        args=[],
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )
    asyncio.run(telegram_bot.chat_stop_command(stop_update, stop_context))

    assert stop_replies == ["MarcBot chat stopped."]
    assert store.get(chat_id=123) is None
