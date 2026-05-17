"""Send generated MarcBot reports through Telegram."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from telegram import Bot

from marcbot.config import MarcBotConfig
from marcbot.errors import MarcBotError
from marcbot.latest_report import validate_latest_daily_status_report
from marcbot.weather_report import find_latest_weather_report

TelegramDocumentSender = Callable[[str, int, Path, str], Awaitable[None]]
TelegramMessageSender = Callable[[str, int, str], Awaitable[None]]
MAX_TELEGRAM_TEXT_CHARS = 3900


@dataclass(frozen=True)
class SendLatestReportResult:
    """Result of sending the latest report."""

    path: Path
    chat_ids: tuple[int, ...]
    report_label: str = "daily status"

    @property
    def message(self) -> str:
        """Return a compact CLI success message."""
        chats = ", ".join(str(chat_id) for chat_id in self.chat_ids)
        return (
            f"Sent latest {self.report_label} report: {self.path.name} "
            f"to chat_id(s): {chats}"
        )


async def _send_telegram_document(
    bot_token: str,
    chat_id: int,
    path: Path,
    caption: str,
) -> None:
    """Send one Telegram document."""
    async with Bot(token=bot_token) as bot:
        with path.open("rb") as file_obj:
            await bot.send_document(
                chat_id=chat_id,
                document=file_obj,
                filename=path.name,
                caption=caption,
            )


async def _send_telegram_message(
    bot_token: str,
    chat_id: int,
    text: str,
) -> None:
    """Send one Telegram text message."""
    async with Bot(token=bot_token) as bot:
        await bot.send_message(chat_id=chat_id, text=text)


def format_weather_report_for_telegram(report_text: str) -> str:
    """Convert a weather Markdown report into bounded Telegram-friendly text."""
    lines = report_text.splitlines()
    output: list[str] = []
    current_heading: str | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("# "):
            output.append("🌤 " + stripped[2:].strip())
            continue

        if stripped.startswith("Generated:"):
            output.append(stripped)
            continue

        if stripped.startswith("Source:") or stripped.startswith("Days requested:"):
            continue

        if stripped == "## Summary":
            output.append("")
            output.append("Summary:")
            continue

        if stripped == "## Detailed forecast":
            output.append("")
            output.append("Detailed forecast:")
            continue

        if stripped.startswith("- "):
            output.append(stripped)
            continue

        if stripped.startswith("### "):
            current_heading = stripped[4:].strip()
            continue

        if current_heading is not None:
            output.append("")
            output.append(f"{current_heading}: {stripped}")
            current_heading = None
            continue

        output.append(stripped)

    message = "\n".join(output).strip()
    if len(message) <= MAX_TELEGRAM_TEXT_CHARS:
        return message

    return message[: MAX_TELEGRAM_TEXT_CHARS - 40].rstrip() + "\n\n[truncated]"


def _validate_telegram_report_config(config: MarcBotConfig) -> None:
    """Validate Telegram config for report sending."""
    if not config.telegram.enabled:
        raise MarcBotError(
            "MBOT-REPORT-SEND-001",
            "Telegram is disabled in config",
        )

    if not config.telegram.bot_token.strip():
        raise MarcBotError(
            "MBOT-REPORT-SEND-002",
            "Telegram bot token is empty",
        )

    if not config.telegram.allowed_chat_ids:
        raise MarcBotError(
            "MBOT-REPORT-SEND-003",
            "No Telegram allowed_chat_ids are configured",
        )


async def send_latest_report_async(
    config: MarcBotConfig,
    sender: TelegramDocumentSender = _send_telegram_document,
) -> SendLatestReportResult:
    """Send the newest generated daily status report to configured chat IDs."""
    _validate_telegram_report_config(config)

    report_result = validate_latest_daily_status_report()
    if not report_result.ok or report_result.path is None:
        raise MarcBotError("MBOT-REPORT-SEND-004", report_result.message)

    caption = f"🤖 MarcBot latest daily status report: {report_result.path.name}"

    for chat_id in config.telegram.allowed_chat_ids:
        try:
            await sender(
                config.telegram.bot_token,
                chat_id,
                report_result.path,
                caption,
            )
        except Exception as exc:
            raise MarcBotError(
                "MBOT-REPORT-SEND-005",
                f"Failed to send report to chat_id {chat_id}: {exc}",
            ) from exc

    return SendLatestReportResult(
        path=report_result.path,
        chat_ids=config.telegram.allowed_chat_ids,
    )


def send_latest_report(
    config: MarcBotConfig,
    sender: TelegramDocumentSender = _send_telegram_document,
) -> SendLatestReportResult:
    """Synchronous wrapper for sending the newest daily status report."""
    return asyncio.run(send_latest_report_async(config, sender=sender))


async def send_latest_weather_report_async(
    config: MarcBotConfig,
    sender: TelegramDocumentSender = _send_telegram_document,
) -> SendLatestReportResult:
    """Send the newest generated weather report to configured chat IDs."""
    _validate_telegram_report_config(config)

    latest = find_latest_weather_report()
    if latest is None:
        raise MarcBotError(
            "MBOT-WEATHER-SEND-001",
            "No weather reports found.",
        )

    caption = f"🤖 MarcBot latest weather report: {latest.name}"

    for chat_id in config.telegram.allowed_chat_ids:
        try:
            await sender(
                config.telegram.bot_token,
                chat_id,
                latest,
                caption,
            )
        except Exception as exc:
            raise MarcBotError(
                "MBOT-WEATHER-SEND-002",
                f"Failed to send weather report to chat_id {chat_id}: {exc}",
            ) from exc

    return SendLatestReportResult(
        path=latest,
        chat_ids=config.telegram.allowed_chat_ids,
        report_label="weather",
    )


def send_latest_weather_report(
    config: MarcBotConfig,
    sender: TelegramDocumentSender = _send_telegram_document,
) -> SendLatestReportResult:
    """Synchronous wrapper for sending the newest weather report."""
    return asyncio.run(send_latest_weather_report_async(config, sender=sender))


async def send_latest_weather_report_text_async(
    config: MarcBotConfig,
    sender: TelegramMessageSender = _send_telegram_message,
) -> SendLatestReportResult:
    """Send the newest generated weather report as Telegram text."""
    _validate_telegram_report_config(config)

    latest = find_latest_weather_report()
    if latest is None:
        raise MarcBotError(
            "MBOT-WEATHER-SEND-003",
            "No weather reports found.",
        )

    message = format_weather_report_for_telegram(latest.read_text(encoding="utf-8"))

    for chat_id in config.telegram.allowed_chat_ids:
        try:
            await sender(config.telegram.bot_token, chat_id, message)
        except Exception as exc:
            raise MarcBotError(
                "MBOT-WEATHER-SEND-004",
                f"Failed to send weather report text to chat_id {chat_id}: {exc}",
            ) from exc

    return SendLatestReportResult(
        path=latest,
        chat_ids=config.telegram.allowed_chat_ids,
        report_label="weather text",
    )


def send_latest_weather_report_text(
    config: MarcBotConfig,
    sender: TelegramMessageSender = _send_telegram_message,
) -> SendLatestReportResult:
    """Synchronous wrapper for sending the newest weather report as text."""
    return asyncio.run(send_latest_weather_report_text_async(config, sender=sender))
