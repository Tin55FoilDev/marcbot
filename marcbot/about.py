"""MarcBot about text."""

from marcbot import __version__


def format_about_message() -> str:
    """Return MarcBot's operator-facing about message."""
    return (
        "🤖 MarcBot about\n"
        f"Version: {__version__}\n"
        "Purpose: personal Telegram operations bot\n"
        "Service: marcbot-telegram.service\n"
        "Repo: /srv/marcbot/app\n"
        "Workspace: /srv/marcbot/workspace\n"
        "Docs: /docs\n"
        "Restore drill: /doc restore\n"
        "Backup status: /backup_status\n"
        "File discovery: /ls\n"
        "File retrieval: /send <workspace-relative-path>\n"
        "Safety: read-only ops by default; no arbitrary shell execution"
    )
