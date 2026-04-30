"""Safe application log reader for MarcBot."""

from __future__ import annotations

import re
from pathlib import Path

from marcbot.config import DEFAULT_CONFIG_PATH, load_config
from marcbot.paths import LOG_DIR

DEFAULT_LOG_FILE = LOG_DIR / "marcbot.log"
DEFAULT_LOG_LINES = 20
MAX_TELEGRAM_MESSAGE_CHARS = 3500

# Matches plain Telegram tokens and Telegram API URL fragments such as:
# 1234567890:ABC...
# bot1234567890:ABC...
_TELEGRAM_TOKEN_RE = re.compile(r"\b(?:bot)?\d{6,16}:[A-Za-z0-9_-]{10,}\b")


def _configured_bot_token() -> str:
    """Return the configured Telegram bot token, or an empty string."""
    try:
        config = load_config(DEFAULT_CONFIG_PATH)
    except Exception:
        return ""

    return config.telegram.bot_token.strip()


def redact_sensitive_text(text: str) -> str:
    """Redact obvious sensitive strings from log text."""
    redacted = text

    token = _configured_bot_token()
    if token:
        redacted = redacted.replace(token, "[REDACTED-TELEGRAM-TOKEN]")
        redacted = redacted.replace(f"bot{token}", "bot[REDACTED-TELEGRAM-TOKEN]")

    redacted = _TELEGRAM_TOKEN_RE.sub("[REDACTED-TELEGRAM-TOKEN]", redacted)
    return redacted


def read_last_log_lines(
    log_file: Path = DEFAULT_LOG_FILE,
    *,
    line_count: int = DEFAULT_LOG_LINES,
) -> str:
    """Read the last N lines from the MarcBot application log."""
    if line_count < 1:
        line_count = DEFAULT_LOG_LINES

    if not log_file.is_file():
        return f"Log file not found: {log_file}"

    try:
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return f"Unable to read log file: {exc}"

    tail = lines[-line_count:]
    if not tail:
        return "Log file is empty."

    return redact_sensitive_text("\n".join(tail))


def format_logs_message(log_text: str) -> str:
    """Format log text for Telegram output."""
    message = f"🤖 MarcBot logs - last {DEFAULT_LOG_LINES} lines\n\n{log_text}"

    if len(message) <= MAX_TELEGRAM_MESSAGE_CHARS:
        return message

    truncated = message[-MAX_TELEGRAM_MESSAGE_CHARS:]
    return "🤖 MarcBot logs - truncated\n\n" + truncated
