"""Foreground Telegram bot for MarcBot."""

from __future__ import annotations

import logging
import platform
import sys
from datetime import UTC, datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from marcbot import __version__
from marcbot.backup_status import format_backup_status_message
from marcbot.config import MarcBotConfig
from marcbot.disk import format_disk_report
from marcbot.docs_index import format_doc_message, format_docs_index, validate_send_doc
from marcbot.errors import MarcBotError
from marcbot.git_status import format_git_report
from marcbot.health import format_health_report, run_health_checks
from marcbot.log_reader import format_logs_message, read_last_log_lines
from marcbot.service_status import format_service_report
from marcbot.tail_reader import format_tail_message
from marcbot.uptime import format_uptime_report
from marcbot.workspace_sender import validate_workspace_send

LOGGER = logging.getLogger(__name__)


def _chat_id_from_update(update: Update) -> int | None:
    """Return the Telegram chat ID from an update, if present."""
    if update.effective_chat is None:
        return None
    return update.effective_chat.id


def is_authorized_chat(chat_id: int | None, allowed_chat_ids: tuple[int, ...]) -> bool:
    """Return whether a chat ID is allowed to use MarcBot.

    If allowed_chat_ids is empty, no chats are authorized. This avoids
    accidentally allowing all Telegram chats when a token is configured.
    """
    if chat_id is None:
        return False
    return chat_id in allowed_chat_ids


async def _reject_unauthorized(update: Update) -> None:
    """Send a generic unauthorized response."""
    if update.message is not None:
        await update.message.reply_text("Unauthorized chat.")


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ping."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /ping from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /ping for chat_id=%s", chat_id)

    if update.message is not None:
        await update.message.reply_text("🤖 MarcBot pong")


async def version_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /version."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /version from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /version for chat_id=%s", chat_id)

    version_text = (
        "🤖 MarcBot version\n"
        f"MarcBot: {__version__}\n"
        f"Python: {platform.python_version()}\n"
        f"Executable: {sys.executable}"
    )

    if update.message is not None:
        await update.message.reply_text(version_text)


async def uptime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /uptime."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    process_started_at = context.application.bot_data["process_started_at"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /uptime from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /uptime for chat_id=%s", chat_id)
    uptime_text = format_uptime_report(process_started_at=process_started_at)

    if update.message is not None:
        await update.message.reply_text(uptime_text)


async def disk_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /disk."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /disk from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /disk for chat_id=%s", chat_id)
    disk_text = format_disk_report()

    if update.message is not None:
        await update.message.reply_text(disk_text)


async def service_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /service."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /service from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /service for chat_id=%s", chat_id)
    service_text = format_service_report()

    if update.message is not None:
        await update.message.reply_text(service_text)


async def git_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /git."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /git from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /git for chat_id=%s", chat_id)
    git_text = format_git_report()

    if update.message is not None:
        await update.message.reply_text(git_text)


async def docs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /docs."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /docs from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /docs for chat_id=%s", chat_id)
    docs_text = format_docs_index()

    if update.message is not None:
        await update.message.reply_text(docs_text)


async def doc_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /doc <name>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /doc from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    doc_name = " ".join(context.args).strip()
    LOGGER.info("Handled /doc for chat_id=%s doc_name=%s", chat_id, doc_name or "<empty>")
    doc_text = format_doc_message(doc_name)

    if update.message is not None:
        await update.message.reply_text(doc_text)


async def senddoc_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /senddoc <name>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /senddoc from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    doc_name = " ".join(context.args).strip()
    result = validate_send_doc(doc_name)
    LOGGER.info(
        "Handled /senddoc for chat_id=%s doc_name=%s ok=%s",
        chat_id,
        doc_name or "<empty>",
        result.ok,
    )

    if update.message is None:
        return

    if not result.ok or result.entry is None:
        await update.message.reply_text(result.message)
        return

    await update.message.reply_document(
        document=result.entry.path,
        filename=result.entry.path.name,
        caption=f"🤖 MarcBot doc: {result.entry.name} - {result.entry.title}",
    )


async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /send <workspace-relative-path>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /send from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    requested_path = " ".join(context.args).strip()
    result = validate_workspace_send(requested_path)
    LOGGER.info(
        "Handled /send for chat_id=%s requested_path=%s ok=%s",
        chat_id,
        requested_path or "<empty>",
        result.ok,
    )

    if update.message is None:
        return

    if not result.ok or result.path is None:
        await update.message.reply_text(result.message)
        return

    await update.message.reply_document(
        document=result.path,
        filename=result.path.name,
        caption=f"🤖 MarcBot workspace file: {requested_path}",
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    app_environment = context.application.bot_data["app_environment"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /status from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /status for chat_id=%s", chat_id)

    status_text = (
        "🤖 MarcBot status\n"
        "Service: running\n"
        f"Version: {__version__}\n"
        f"Environment: {app_environment}"
    )

    if update.message is not None:
        await update.message.reply_text(status_text)


async def backup_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /backup_status."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /backup_status from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /backup_status for chat_id=%s", chat_id)
    backup_text = format_backup_status_message()

    if update.message is not None:
        await update.message.reply_text(backup_text)


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /health."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /health from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /health for chat_id=%s", chat_id)
    health_text = format_health_report(run_health_checks())

    if update.message is not None:
        await update.message.reply_text(health_text)


async def tail_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tail <approved-log-name>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /tail from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    tail_name = " ".join(context.args).strip()
    LOGGER.info("Handled /tail for chat_id=%s tail_name=%s", chat_id, tail_name or "<empty>")
    tail_text = format_tail_message(tail_name)

    if update.message is not None:
        await update.message.reply_text(tail_text)


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /logs."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /logs from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /logs for chat_id=%s", chat_id)
    logs_text = format_logs_message(read_last_log_lines())

    if update.message is not None:
        await update.message.reply_text(logs_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /help from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /help for chat_id=%s", chat_id)

    help_text = (
        "🤖 MarcBot commands:\n"
        "/ping - check whether MarcBot is responding\n"
        "/version - show MarcBot and Python version\n"
        "/uptime - show host and MarcBot process uptime\n"
        "/disk - show disk usage for root and /srv/marcbot\n"
        "/service - show MarcBot systemd service state\n"
        "/git - show MarcBot repository status\n"
        "/docs - list approved MarcBot docs\n"
        "/doc <name> - show an approved MarcBot doc preview\n"
        "/senddoc <name> - send an approved MarcBot doc as a file\n"
        "/send <workspace-relative-path> - send a file from /srv/marcbot/workspace\n"
        "/status - show basic MarcBot service status\n"
        "/health - run local MarcBot health checks\n"
        "/backup_status - show latest MarcBot app-level backup status\n"
        "/logs - show recent MarcBot application logs\n"
        "/tail <app|service> - show approved diagnostic log tails\n"
        "/help - show this help message"
    )

    if update.message is not None:
        await update.message.reply_text(help_text)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown slash commands."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized unknown command from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    command_text = "<unknown>"
    if update.message is not None and update.message.text:
        command_text = update.message.text.split()[0]

    LOGGER.info("Handled unknown command for chat_id=%s command=%s", chat_id, command_text)

    if update.message is not None:
        await update.message.reply_text(
            "🤖 MarcBot\n"
            f"Unknown command: {command_text}\n"
            "Use /help to see available commands."
        )


def build_application(config: MarcBotConfig) -> Application:
    """Build a Telegram Application from validated MarcBot config."""
    if not config.telegram.enabled:
        raise MarcBotError("MBOT-TELEGRAM-001", "Telegram is disabled in config")

    if not config.telegram.bot_token.strip():
        raise MarcBotError("MBOT-TELEGRAM-002", "Telegram bot token is empty")

    if not config.telegram.allowed_chat_ids:
        raise MarcBotError(
            "MBOT-TELEGRAM-003",
            "Telegram is enabled but no allowed_chat_ids are configured",
        )

    application = Application.builder().token(config.telegram.bot_token).build()
    application.bot_data["allowed_chat_ids"] = config.telegram.allowed_chat_ids
    application.bot_data["app_environment"] = config.app.environment
    application.bot_data["process_started_at"] = datetime.now(UTC)

    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("version", version_command))
    application.add_handler(CommandHandler("uptime", uptime_command))
    application.add_handler(CommandHandler("disk", disk_command))
    application.add_handler(CommandHandler("service", service_command))
    application.add_handler(CommandHandler("git", git_command))
    application.add_handler(CommandHandler("docs", docs_command))
    application.add_handler(CommandHandler("doc", doc_command))
    application.add_handler(CommandHandler("senddoc", senddoc_command))
    application.add_handler(CommandHandler("send", send_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("health", health_command))
    application.add_handler(CommandHandler("backup_status", backup_status_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("tail", tail_command))
    application.add_handler(CommandHandler("help", help_command))

    # This must remain after all known command handlers.
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    return application


def run_foreground_bot(config: MarcBotConfig) -> None:
    """Run the Telegram bot in foreground polling mode."""
    application = build_application(config)
    LOGGER.info("Starting Telegram polling bot")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
