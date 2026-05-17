"""Tests for MarcBot report sending."""

from pathlib import Path

import pytest

from marcbot import report_sender
from marcbot.config import AppConfig, MarcBotConfig, TelegramConfig
from marcbot.errors import MarcBotError


def _config(
    *,
    enabled: bool = True,
    bot_token: str = "test-token",
    allowed_chat_ids: tuple[int, ...] = (12345,),
) -> MarcBotConfig:
    return MarcBotConfig(
        app=AppConfig(name="MarcBot", environment="test"),
        telegram=TelegramConfig(
            enabled=enabled,
            bot_token=bot_token,
            allowed_chat_ids=allowed_chat_ids,
        ),
    )


def test_validate_telegram_report_config_rejects_disabled_telegram() -> None:
    with pytest.raises(MarcBotError, match="Telegram is disabled"):
        report_sender._validate_telegram_report_config(_config(enabled=False))


def test_validate_telegram_report_config_rejects_empty_token() -> None:
    with pytest.raises(MarcBotError, match="Telegram bot token is empty"):
        report_sender._validate_telegram_report_config(_config(bot_token=""))


def test_validate_telegram_report_config_rejects_no_chat_ids() -> None:
    with pytest.raises(MarcBotError, match="No Telegram allowed_chat_ids"):
        report_sender._validate_telegram_report_config(_config(allowed_chat_ids=()))


def test_send_latest_report_async_sends_to_all_configured_chats(monkeypatch, tmp_path) -> None:
    report = tmp_path / "daily-status-2026-05-01.md"
    report.write_text("report\n", encoding="utf-8")
    sends: list[tuple[str, int, Path, str]] = []

    class FakeLatestReportResult:
        ok = True
        path = report
        message = "ok"

    async def fake_sender(bot_token: str, chat_id: int, path: Path, caption: str) -> None:
        sends.append((bot_token, chat_id, path, caption))

    monkeypatch.setattr(
        report_sender,
        "validate_latest_daily_status_report",
        lambda: FakeLatestReportResult(),
    )

    result = report_sender.send_latest_report(
        _config(allowed_chat_ids=(111, 222)),
        sender=fake_sender,
    )

    expected_caption = "🤖 MarcBot latest daily status report: daily-status-2026-05-01.md"

    assert result.path == report
    assert result.chat_ids == (111, 222)
    assert "daily-status-2026-05-01.md" in result.message
    assert sends == [
        ("test-token", 111, report, expected_caption),
        ("test-token", 222, report, expected_caption),
    ]


def test_send_latest_report_async_rejects_missing_report(monkeypatch) -> None:
    class FakeLatestReportResult:
        ok = False
        path = None
        message = "No daily status reports found"

    monkeypatch.setattr(
        report_sender,
        "validate_latest_daily_status_report",
        lambda: FakeLatestReportResult(),
    )

    with pytest.raises(MarcBotError, match="No daily status reports found"):
        report_sender.send_latest_report(_config())


def test_send_latest_report_async_wraps_send_failure(monkeypatch, tmp_path) -> None:
    report = tmp_path / "daily-status-2026-05-01.md"
    report.write_text("report\n", encoding="utf-8")

    class FakeLatestReportResult:
        ok = True
        path = report
        message = "ok"

    async def fake_sender(bot_token: str, chat_id: int, path: Path, caption: str) -> None:
        raise RuntimeError("network unavailable")

    monkeypatch.setattr(
        report_sender,
        "validate_latest_daily_status_report",
        lambda: FakeLatestReportResult(),
    )

    with pytest.raises(MarcBotError, match="Failed to send report to chat_id 12345"):
        report_sender.send_latest_report(_config(), sender=fake_sender)

def test_send_latest_weather_report_sends_to_all_configured_chats(
    monkeypatch,
    tmp_path,
) -> None:
    weather_report = tmp_path / "weather-report-2026-05-17-080000.md"
    weather_report.write_text("# Weather", encoding="utf-8")

    monkeypatch.setattr(
        report_sender,
        "find_latest_weather_report",
        lambda: weather_report,
    )

    sent = []

    async def fake_sender(bot_token, chat_id, path, caption):
        sent.append((bot_token, chat_id, path, caption))

    result = report_sender.send_latest_weather_report(_config(), sender=fake_sender)

    assert result.path == weather_report
    assert result.chat_ids == (12345,)
    assert result.report_label == "weather"
    assert result.message == (
        "Sent latest weather report: weather-report-2026-05-17-080000.md "
        "to chat_id(s): 12345"
    )
    assert sent == [
        (
            "test-token",
            12345,
            weather_report,
            "🤖 MarcBot latest weather report: weather-report-2026-05-17-080000.md",
        )
    ]


def test_send_latest_weather_report_rejects_missing_report(monkeypatch) -> None:
    monkeypatch.setattr(report_sender, "find_latest_weather_report", lambda: None)

    with pytest.raises(MarcBotError) as excinfo:
        report_sender.send_latest_weather_report(_config())

    assert excinfo.value.code == "MBOT-WEATHER-SEND-001"


def test_send_latest_weather_report_wraps_send_failure(monkeypatch, tmp_path) -> None:
    weather_report = tmp_path / "weather-report-2026-05-17-080000.md"
    weather_report.write_text("# Weather", encoding="utf-8")

    monkeypatch.setattr(
        report_sender,
        "find_latest_weather_report",
        lambda: weather_report,
    )

    async def fake_sender(bot_token, chat_id, path, caption):
        raise RuntimeError("telegram down")

    with pytest.raises(MarcBotError) as excinfo:
        report_sender.send_latest_weather_report(_config(), sender=fake_sender)

    assert excinfo.value.code == "MBOT-WEATHER-SEND-002"
