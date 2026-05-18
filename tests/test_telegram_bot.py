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

def test_normal_text_is_ignored_when_chat_inactive(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    replies = []

    class FakeMessage:
        text = "hello"

        async def reply_text(self, text):
            replies.append(text)

    store = telegram_bot.ChatSessionStore()
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_text_message(update, context))

    assert replies == []


def test_active_chat_text_calls_configured_profile(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot
    from marcbot.llm_client import LlmCompletionResult

    replies = []

    class FakeMessage:
        text = "Explain VLANs briefly."

        async def reply_text(self, text):
            replies.append(text)

    provider = SimpleNamespace(name="lmstudio")
    profile = SimpleNamespace(
        name="local_fast",
        provider="lmstudio",
        model="test-model",
        temperature=0.2,
        max_tokens=100,
        chat_enabled=True,
    )

    store = telegram_bot.ChatSessionStore()
    store.start(chat_id=123, profile_name="local_fast")
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)
    monkeypatch.setattr(
        telegram_bot,
        "load_llm_config",
        lambda: SimpleNamespace(
            providers={"lmstudio": provider},
            profiles={"local_fast": profile},
        ),
    )

    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        return LlmCompletionResult(
            provider_name="lmstudio",
            profile_name="local_fast",
            model="test-model",
            response_text="A VLAN separates network traffic logically.",
            finish_reason="stop",
        )

    monkeypatch.setattr(
        telegram_bot,
        "run_openai_compatible_completion",
        fake_completion,
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_text_message(update, context))

    assert replies == ["A VLAN separates network traffic logically."]
    assert len(calls) == 1
    assert calls[0]["provider"] is provider
    assert calls[0]["profile_name"] == "local_fast"
    assert calls[0]["model"] == "test-model"
    assert "Explain VLANs briefly." in calls[0]["prompt"]

    session = store.get(chat_id=123)
    assert session is not None
    assert [message.role for message in session.history] == ["user", "assistant"]


def test_active_chat_rejects_too_long_input(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    replies = []

    class FakeMessage:
        text = "x" * (telegram_bot.MAX_CHAT_INPUT_CHARS + 1)

        async def reply_text(self, text):
            replies.append(text)

    store = telegram_bot.ChatSessionStore()
    store.start(chat_id=123, profile_name="local_fast")
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_text_message(update, context))

    assert replies == [
        f"Chat message is too long. Limit: {telegram_bot.MAX_CHAT_INPUT_CHARS} characters."
    ]


def test_active_chat_stops_if_profile_no_longer_chat_enabled(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    replies = []

    class FakeMessage:
        text = "hello"

        async def reply_text(self, text):
            replies.append(text)

    profile = SimpleNamespace(
        name="local_fast",
        provider="lmstudio",
        chat_enabled=False,
    )

    store = telegram_bot.ChatSessionStore()
    store.start(chat_id=123, profile_name="local_fast")
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)
    monkeypatch.setattr(
        telegram_bot,
        "load_llm_config",
        lambda: SimpleNamespace(
            providers={},
            profiles={"local_fast": profile},
        ),
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_text_message(update, context))

    assert replies == [
        "Chat stopped: profile is no longer approved for chat: local_fast"
    ]
    assert store.get(chat_id=123) is None


def test_active_chat_provider_error_is_clean(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot
    from marcbot.errors import MarcBotError

    replies = []

    class FakeMessage:
        text = "hello"

        async def reply_text(self, text):
            replies.append(text)

    provider = SimpleNamespace(name="lmstudio")
    profile = SimpleNamespace(
        name="local_fast",
        provider="lmstudio",
        model="test-model",
        temperature=0.2,
        max_tokens=100,
        chat_enabled=True,
    )

    store = telegram_bot.ChatSessionStore()
    store.start(chat_id=123, profile_name="local_fast")
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)
    monkeypatch.setattr(
        telegram_bot,
        "load_llm_config",
        lambda: SimpleNamespace(
            providers={"lmstudio": provider},
            profiles={"local_fast": profile},
        ),
    )

    def fake_completion(**kwargs):
        raise MarcBotError("MBOT-TEST", "provider unavailable")

    monkeypatch.setattr(
        telegram_bot,
        "run_openai_compatible_completion",
        fake_completion,
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_text_message(update, context))

    assert replies == ["Chat provider error: provider unavailable"]
    session = store.get(chat_id=123)
    assert session is not None
    assert session.history == []

def test_active_chat_includes_local_context_in_prompt(monkeypatch, tmp_path) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot
    from marcbot.chat_context import load_chat_context
    from marcbot.llm_client import LlmCompletionResult

    (tmp_path / "agent.md").write_text(
        "Name: MarcBot\nHumor: light and occasional",
        encoding="utf-8",
    )
    (tmp_path / "user.md").write_text(
        "Marc prefers numbered steps.",
        encoding="utf-8",
    )

    replies = []

    class FakeMessage:
        text = "Say hello."

        async def reply_text(self, text):
            replies.append(text)

    provider = SimpleNamespace(name="lmstudio")
    profile = SimpleNamespace(
        name="local_fast",
        provider="lmstudio",
        model="test-model",
        temperature=0.2,
        max_tokens=100,
        chat_enabled=True,
    )

    store = telegram_bot.ChatSessionStore()
    store.start(chat_id=123, profile_name="local_fast")
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)
    monkeypatch.setattr(
        telegram_bot,
        "load_llm_config",
        lambda: SimpleNamespace(
            providers={"lmstudio": provider},
            profiles={"local_fast": profile},
        ),
    )
    monkeypatch.setattr(
        telegram_bot,
        "load_chat_context",
        lambda: load_chat_context(context_dir=tmp_path),
    )

    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        return LlmCompletionResult(
            provider_name="lmstudio",
            profile_name="local_fast",
            model="test-model",
            response_text="Hello from MarcBot.",
            finish_reason="stop",
        )

    monkeypatch.setattr(
        telegram_bot,
        "run_openai_compatible_completion",
        fake_completion,
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_text_message(update, context))

    assert replies == ["Hello from MarcBot."]
    assert len(calls) == 1
    prompt = calls[0]["prompt"]
    assert "Local configured chat context:" in prompt
    assert "## Local chat context: agent.md" in prompt
    assert "Name: MarcBot" in prompt
    assert "Humor: light and occasional" in prompt
    assert "## Local chat context: user.md" in prompt
    assert "Marc prefers numbered steps." in prompt
    assert "Say hello." in prompt


def test_active_chat_allows_missing_local_context(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot
    from marcbot.chat_context import load_chat_context
    from marcbot.llm_client import LlmCompletionResult

    replies = []

    class FakeMessage:
        text = "hello"

        async def reply_text(self, text):
            replies.append(text)

    provider = SimpleNamespace(name="lmstudio")
    profile = SimpleNamespace(
        name="local_fast",
        provider="lmstudio",
        model="test-model",
        temperature=0.2,
        max_tokens=100,
        chat_enabled=True,
    )

    store = telegram_bot.ChatSessionStore()
    store.start(chat_id=123, profile_name="local_fast")
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)
    monkeypatch.setattr(
        telegram_bot,
        "load_llm_config",
        lambda: SimpleNamespace(
            providers={"lmstudio": provider},
            profiles={"local_fast": profile},
        ),
    )
    monkeypatch.setattr(telegram_bot, "load_chat_context", load_chat_context)

    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        return LlmCompletionResult(
            provider_name="lmstudio",
            profile_name="local_fast",
            model="test-model",
            response_text="hello",
            finish_reason="stop",
        )

    monkeypatch.setattr(
        telegram_bot,
        "run_openai_compatible_completion",
        fake_completion,
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_text_message(update, context))

    assert replies == ["hello"]
    assert len(calls) == 1


def test_active_chat_context_error_is_clean(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot
    from marcbot.errors import MarcBotError

    replies = []

    class FakeMessage:
        text = "hello"

        async def reply_text(self, text):
            replies.append(text)

    provider = SimpleNamespace(name="lmstudio")
    profile = SimpleNamespace(
        name="local_fast",
        provider="lmstudio",
        model="test-model",
        temperature=0.2,
        max_tokens=100,
        chat_enabled=True,
    )

    store = telegram_bot.ChatSessionStore()
    store.start(chat_id=123, profile_name="local_fast")
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)
    monkeypatch.setattr(
        telegram_bot,
        "load_llm_config",
        lambda: SimpleNamespace(
            providers={"lmstudio": provider},
            profiles={"local_fast": profile},
        ),
    )

    def fail_context():
        raise MarcBotError("MBOT-CHATCTX-TEST", "context too large")

    monkeypatch.setattr(telegram_bot, "load_chat_context", fail_context)

    def fail_completion(**kwargs):
        raise AssertionError("provider should not be contacted")

    monkeypatch.setattr(
        telegram_bot,
        "run_openai_compatible_completion",
        fail_completion,
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_text_message(update, context))

    assert replies == ["Chat context error: context too large"]
    session = store.get(chat_id=123)
    assert session is not None
    assert session.history == []

def test_format_chat_prompt_uses_explicit_final_response_instruction() -> None:
    import marcbot.telegram_bot as telegram_bot

    prompt = telegram_bot._format_chat_prompt(
        history=[],
        user_text="Briefly introduce yourself.",
        local_context="Name: MarcBot",
    )

    assert "Current user message:" in prompt
    assert "Briefly introduce yourself." in prompt
    assert "Respond now with the assistant message only." in prompt
    assert not prompt.endswith("assistant:")

def test_format_chat_prompt_allows_configured_local_context_size() -> None:
    import marcbot.telegram_bot as telegram_bot

    local_context = "x" * 7000
    prompt = telegram_bot._format_chat_prompt(
        history=[],
        user_text="Briefly introduce yourself.",
        local_context=local_context,
    )

    assert len(prompt) < telegram_bot.MAX_CHAT_PROMPT_CHARS
    assert telegram_bot.MAX_CHAT_PROMPT_CHARS == 12000

def test_chat_context_command_reports_loaded_context_without_contents(
    monkeypatch, tmp_path
) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot
    from marcbot.chat_context import load_chat_context

    (tmp_path / "agent.md").write_text(
        "Private agent context should not appear",
        encoding="utf-8",
    )

    replies = []

    class FakeMessage:
        async def reply_text(self, text):
            replies.append(text)

    monkeypatch.setattr(
        telegram_bot,
        "load_chat_context",
        lambda: load_chat_context(context_dir=tmp_path),
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_context_command(update, context))

    assert len(replies) == 1
    assert "MarcBot chat context" in replies[0]
    assert "- agent.md: loaded" in replies[0]
    assert "- system.md: missing" in replies[0]
    assert "Provider contact: no" in replies[0]
    assert "Private agent context should not appear" not in replies[0]


def test_chat_context_command_reports_context_error(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot
    from marcbot.errors import MarcBotError

    replies = []

    class FakeMessage:
        async def reply_text(self, text):
            replies.append(text)

    def fail_context():
        raise MarcBotError("MBOT-CHATCTX-TEST", "context too large")

    monkeypatch.setattr(telegram_bot, "load_chat_context", fail_context)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_context_command(update, context))

    assert replies == ["Chat context error: context too large"]


def test_chat_context_command_is_registered() -> None:
    application = build_application(make_config())
    command_names = {
        command
        for handlers in application.handlers.values()
        for handler in handlers
        if hasattr(handler, "commands")
        for command in handler.commands
    }

    assert "chat_context" in command_names

def test_active_chat_sends_typing_action_before_provider_call(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot
    from marcbot.chat_context import load_chat_context
    from marcbot.llm_client import LlmCompletionResult

    replies = []
    actions = []

    class FakeMessage:
        text = "hello"

        async def reply_text(self, text):
            replies.append(text)

    class FakeBot:
        async def send_chat_action(self, chat_id, action):
            actions.append((chat_id, action))

    provider = SimpleNamespace(name="lmstudio")
    profile = SimpleNamespace(
        name="local_fast",
        provider="lmstudio",
        model="test-model",
        temperature=0.2,
        max_tokens=100,
        chat_enabled=True,
    )

    store = telegram_bot.ChatSessionStore()
    store.start(chat_id=123, profile_name="local_fast")
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)
    monkeypatch.setattr(
        telegram_bot,
        "load_llm_config",
        lambda: SimpleNamespace(
            providers={"lmstudio": provider},
            profiles={"local_fast": profile},
        ),
    )
    monkeypatch.setattr(telegram_bot, "load_chat_context", load_chat_context)

    def fake_completion(**kwargs):
        return LlmCompletionResult(
            provider_name="lmstudio",
            profile_name="local_fast",
            model="test-model",
            response_text="hello Marc",
            finish_reason="stop",
        )

    monkeypatch.setattr(
        telegram_bot,
        "run_openai_compatible_completion",
        fake_completion,
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        bot=FakeBot(),
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_text_message(update, context))

    assert actions == [(123, "typing")]
    assert replies == ["hello Marc"]


def test_inactive_chat_does_not_send_typing_action(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    actions = []
    replies = []

    class FakeMessage:
        text = "hello"

        async def reply_text(self, text):
            replies.append(text)

    class FakeBot:
        async def send_chat_action(self, chat_id, action):
            actions.append((chat_id, action))

    store = telegram_bot.ChatSessionStore()
    monkeypatch.setattr(telegram_bot, "CHAT_SESSIONS", store)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        bot=FakeBot(),
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_text_message(update, context))

    assert actions == []
    assert replies == []

def test_chat_profiles_command_reports_profiles_without_provider_contact(
    monkeypatch,
) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    replies = []

    class FakeMessage:
        async def reply_text(self, text):
            replies.append(text)

    monkeypatch.setattr(
        telegram_bot,
        "load_llm_config",
        lambda: SimpleNamespace(
            profiles={
                "local_fast": SimpleNamespace(
                    name="local_fast",
                    model="google/gemma-4-e4b",
                    intended_use="low_risk_utility",
                    chat_enabled=True,
                ),
                "local_careful": SimpleNamespace(
                    name="local_careful",
                    model="qwen3.6-35b-a3b",
                    intended_use="bounded_local_analysis",
                    chat_enabled=False,
                ),
            }
        ),
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_profiles_command(update, context))

    assert len(replies) == 1
    assert "MarcBot chat profiles" in replies[0]
    assert "Provider contact: no" in replies[0]
    assert (
        "- local_fast: chat_enabled=True, model=google/gemma-4-e4b, "
        "intended_use=low_risk_utility"
    ) in replies[0]
    assert (
        "- local_careful: chat_enabled=False, model=qwen3.6-35b-a3b, "
        "intended_use=bounded_local_analysis"
    ) in replies[0]


def test_chat_profiles_command_reports_config_error(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    replies = []

    class FakeMessage:
        async def reply_text(self, text):
            replies.append(text)

    def fail_config():
        raise RuntimeError("boom")

    monkeypatch.setattr(telegram_bot, "load_llm_config", fail_config)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.chat_profiles_command(update, context))

    assert replies == ["Chat profiles unavailable: LLM config unavailable."]


def test_chat_profiles_command_is_registered() -> None:
    application = build_application(make_config())
    command_names = {
        command
        for handlers in application.handlers.values()
        for handler in handlers
        if hasattr(handler, "commands")
        for command in handler.commands
    }

    assert "chat_profiles" in command_names

def test_weather_status_command_replies_with_status(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    replies = []

    class FakeMessage:
        async def reply_text(self, text):
            replies.append(text)

    monkeypatch.setattr(
        telegram_bot,
        "format_weather_status_message",
        lambda: "MarcBot weather report\nProvider contact: no",
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.weather_status_command(update, context))

    assert replies == ["MarcBot weather report\nProvider contact: no"]


def test_weather_status_command_is_registered() -> None:
    application = build_application(make_config())
    command_names = {
        command
        for handlers in application.handlers.values()
        for handler in handlers
        if hasattr(handler, "commands")
        for command in handler.commands
    }

    assert "weather_status" in command_names

def test_send_weather_report_command_sends_latest_text(monkeypatch, tmp_path) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    report = tmp_path / "weather-report-2026-05-18-071500.md"
    report.write_text("# Westfield Weather\n\n## Summary\n\n- Nice day.\n", encoding="utf-8")

    replies = []

    class FakeMessage:
        async def reply_text(self, text):
            replies.append(text)

    monkeypatch.setattr(telegram_bot, "find_latest_weather_report", lambda: report)
    monkeypatch.setattr(
        telegram_bot,
        "format_weather_report_for_telegram",
        lambda text: "🌤 Westfield Weather\n\nSummary:\n- Nice day.",
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.send_weather_report_command(update, context))

    assert replies == ["🌤 Westfield Weather\n\nSummary:\n- Nice day."]


def test_send_weather_report_command_reports_missing_latest(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    replies = []

    class FakeMessage:
        async def reply_text(self, text):
            replies.append(text)

    monkeypatch.setattr(telegram_bot, "find_latest_weather_report", lambda: None)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.send_weather_report_command(update, context))

    assert replies == ["No weather reports found."]


def test_send_weather_report_command_is_registered() -> None:
    application = build_application(make_config())
    command_names = {
        command
        for handlers in application.handlers.values()
        for handler in handlers
        if hasattr(handler, "commands")
        for command in handler.commands
    }

    assert "send_weather_report" in command_names

def test_memory_status_command_replies_with_status(monkeypatch) -> None:
    import asyncio
    from types import SimpleNamespace

    import marcbot.telegram_bot as telegram_bot

    replies = []

    class FakeMessage:
        async def reply_text(self, text):
            replies.append(text)

    monkeypatch.setattr(
        telegram_bot,
        "format_memory_status_message",
        lambda: "MarcBot memory\nProvider contact: no",
    )

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        message=FakeMessage(),
    )
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"allowed_chat_ids": {123}}),
    )

    asyncio.run(telegram_bot.memory_status_command(update, context))

    assert replies == ["MarcBot memory\nProvider contact: no"]


def test_memory_status_command_is_registered() -> None:
    application = build_application(make_config())
    command_names = {
        command
        for handlers in application.handlers.values()
        for handler in handlers
        if hasattr(handler, "commands")
        for command in handler.commands
    }

    assert "memory_status" in command_names
