"""Tests for approved diagnostic tail readers."""

from pathlib import Path

from marcbot import tail_reader


def test_format_tail_message_rejects_empty_name() -> None:
    message = tail_reader.format_tail_message("")

    assert "Missing tail name" in message
    assert "Use: /tail <app|service>" in message


def test_format_tail_message_rejects_unknown_name() -> None:
    message = tail_reader.format_tail_message("unknown")

    assert "Unknown tail name: unknown" in message
    assert "Available tails: app, service" in message


def test_read_app_tail_missing_file(tmp_path: Path) -> None:
    message = tail_reader.read_app_tail(tmp_path / "missing.log")

    assert "Log file not found" in message


def test_read_app_tail_empty_file(tmp_path: Path) -> None:
    log_file = tmp_path / "empty.log"
    log_file.write_text("", encoding="utf-8")

    message = tail_reader.read_app_tail(log_file)

    assert message == "Log file is empty."


def test_read_app_tail_reads_last_lines(tmp_path: Path) -> None:
    log_file = tmp_path / "app.log"
    log_file.write_text("one\ntwo\nthree\n", encoding="utf-8")

    message = tail_reader.read_app_tail(log_file, line_count=2)

    assert message == "two\nthree"


def test_read_app_tail_redacts_telegram_token(tmp_path: Path) -> None:
    log_file = tmp_path / "app.log"
    log_file.write_text(
        "token 1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ\n",
        encoding="utf-8",
    )

    message = tail_reader.read_app_tail(log_file)

    assert "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in message
    assert "[REDACTED-TELEGRAM-TOKEN]" in message


def test_format_tail_message_app_uses_app_tail(
    tmp_path: Path,
    monkeypatch,
) -> None:
    log_file = tmp_path / "app.log"
    log_file.write_text("hello\n", encoding="utf-8")

    monkeypatch.setattr(tail_reader, "DEFAULT_LOG_FILE", log_file)

    message = tail_reader.format_tail_message("app")

    assert "🤖 MarcBot tail: app" in message
    assert "hello" in message
