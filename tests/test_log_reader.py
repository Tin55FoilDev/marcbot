"""Tests for safe MarcBot log reading."""

from marcbot.log_reader import (
    format_logs_message,
    read_last_log_lines,
    redact_sensitive_text,
)


def test_redact_sensitive_text_redacts_plain_telegram_token() -> None:
    text = "token=123456789:ABCdefGHI_jklMNOpqrSTUvwxYZ123456"

    redacted = redact_sensitive_text(text)

    assert "123456789:ABCdef" not in redacted
    assert "[REDACTED-TELEGRAM-TOKEN]" in redacted


def test_redact_sensitive_text_redacts_bot_prefixed_telegram_token() -> None:
    text = "url=https://api.telegram.org/bot123456789:ABCdefGHI_jklMNOpqrSTUvwxYZ123456/getMe"

    redacted = redact_sensitive_text(text)

    assert "bot123456789:ABCdef" not in redacted
    assert "bot[REDACTED-TELEGRAM-TOKEN]" in redacted or "[REDACTED-TELEGRAM-TOKEN]" in redacted


def test_read_last_log_lines_returns_tail(tmp_path) -> None:
    log_file = tmp_path / "marcbot.log"
    log_file.write_text("one\ntwo\nthree\n", encoding="utf-8")

    result = read_last_log_lines(log_file, line_count=2)

    assert "one" not in result
    assert "two" in result
    assert "three" in result


def test_read_last_log_lines_handles_missing_file(tmp_path) -> None:
    log_file = tmp_path / "missing.log"

    result = read_last_log_lines(log_file)

    assert "Log file not found" in result


def test_format_logs_message_includes_header() -> None:
    message = format_logs_message("line one\nline two")

    assert "🤖 MarcBot logs" in message
    assert "line one" in message
    assert "line two" in message
