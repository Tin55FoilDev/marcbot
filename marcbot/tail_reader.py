"""Approved diagnostic tail readers for MarcBot."""

from __future__ import annotations

import subprocess
from pathlib import Path

from marcbot.log_reader import DEFAULT_LOG_FILE, redact_sensitive_text

DEFAULT_TAIL_LINES = 40
MAX_TAIL_MESSAGE_CHARS = 3500
SERVICE_NAME = "marcbot-telegram.service"
JOURNALCTL_TIMEOUT_SECONDS = 8

APPROVED_TAIL_NAMES = ("app", "service")


def approved_tail_names() -> str:
    """Return approved tail names as a compact string."""
    return ", ".join(APPROVED_TAIL_NAMES)


def _usage() -> str:
    """Return operator-facing tail usage."""
    return "Use: /tail <app|service>"


def _format_error(message: str) -> str:
    """Format a tail error message."""
    return f"🤖 MarcBot tail\n{message}\n{_usage()}"


def _bound_message(message: str) -> str:
    """Keep Telegram output within a conservative size bound."""
    if len(message) <= MAX_TAIL_MESSAGE_CHARS:
        return message

    return "🤖 MarcBot tail - truncated\n\n" + message[-MAX_TAIL_MESSAGE_CHARS:]


def read_app_tail(
    log_file: Path = DEFAULT_LOG_FILE,
    *,
    line_count: int = DEFAULT_TAIL_LINES,
) -> str:
    """Read the last lines from the MarcBot app log."""
    if line_count < 1:
        line_count = DEFAULT_TAIL_LINES

    if not log_file.is_file():
        return f"Log file not found: {log_file}"

    try:
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return f"Unable to read log file: {exc}"

    if not lines:
        return "Log file is empty."

    return redact_sensitive_text("\n".join(lines[-line_count:]))


def read_service_tail(*, line_count: int = DEFAULT_TAIL_LINES) -> str:
    """Read the last journal lines for the fixed MarcBot service."""
    if line_count < 1:
        line_count = DEFAULT_TAIL_LINES

    try:
        result = subprocess.run(
            [
                "journalctl",
                "-q",
                "-u",
                SERVICE_NAME,
                "-n",
                str(line_count),
                "--no-pager",
                "--output=short-iso",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=JOURNALCTL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return "Timed out reading service journal."
    except OSError as exc:
        return f"Unable to read service journal: {exc}"

    output = (result.stdout or result.stderr).strip()
    if not output:
        return "Service journal returned no output."

    return redact_sensitive_text(output)


def format_tail_message(name: str) -> str:
    """Format an approved diagnostic tail response."""
    normalized_name = name.strip().lower()

    if not normalized_name:
        return _format_error("Missing tail name.")

    if normalized_name == "app":
        body = read_app_tail(DEFAULT_LOG_FILE)
        return _bound_message(f"🤖 MarcBot tail: app\n\n{body}")

    if normalized_name == "service":
        body = read_service_tail()
        return _bound_message(f"🤖 MarcBot tail: service\n\n{body}")

    return _format_error(
        f"Unknown tail name: {normalized_name}\nAvailable tails: {approved_tail_names()}",
    )
