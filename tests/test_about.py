"""Tests for MarcBot about text."""

from marcbot import __version__
from marcbot.about import format_about_message


def test_format_about_message_contains_expected_baseline() -> None:
    message = format_about_message()

    assert "🤖 MarcBot about" in message
    assert f"Version: {__version__}" in message
    assert "Purpose: personal Telegram operations bot" in message
    assert "Service: marcbot-telegram.service" in message
    assert "Repo: /srv/marcbot/app" in message
    assert "Workspace: /srv/marcbot/workspace" in message
    assert "Docs: /docs" in message
    assert "Restore drill: /doc restore" in message
    assert "Backup status: /backup_status" in message
    assert "File discovery: /ls" in message
    assert "File retrieval: /send <workspace-relative-path>" in message
    assert "no arbitrary shell execution" in message
