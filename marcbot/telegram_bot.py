"""Foreground Telegram bot for MarcBot."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from marcbot import __version__
from marcbot.config import MarcBotConfig
from marcbot.errors import MarcBotError

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

    if update.message is not None:
        await update.message.reply_text("🤖 MarcBot pong")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    app_environment = context.application.bot_data["app_environment"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /status from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    status_text = (
        "🤖 MarcBot status\n"
        "Service: running\n"
        f"Version: {__version__}\n"
        f"Environment: {app_environment}"
    )

    if update.message is not None:
        await update.message.reply_text(status_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /help from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    help_text = (
        "🤖 MarcBot commands:\n"
        "/ping - check whether MarcBot is responding\n"
        "/status - show basic MarcBot service status\n"
        "/help - show this help message"
    )

    if update.message is not None:
        await update.message.reply_text(help_text)


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

    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("help", help_command))

    return application


def run_foreground_bot(config: MarcBotConfig) -> None:
    """Run the Telegram bot in foreground polling mode."""
    application = build_application(config)
    LOGGER.info("Starting Telegram polling bot")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
