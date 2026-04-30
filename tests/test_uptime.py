"""Tests for MarcBot uptime helpers."""

from datetime import UTC, datetime

from marcbot.uptime import (
    format_duration,
    format_uptime_report,
    process_uptime_seconds,
    read_host_uptime_seconds,
)


def test_format_duration_seconds_only() -> None:
    assert format_duration(9) == "09 seconds"


def test_format_duration_minutes_seconds() -> None:
    assert format_duration(125) == "02 minutes, 05 seconds"


def test_format_duration_days_hours_minutes_seconds() -> None:
    assert format_duration(93_784) == "1 day, 02 hours, 03 minutes, 04 seconds"


def test_read_host_uptime_seconds_from_file(tmp_path) -> None:
    uptime_file = tmp_path / "uptime"
    uptime_file.write_text("123.45 678.90\n", encoding="utf-8")

    assert read_host_uptime_seconds(uptime_file) == 123.45


def test_process_uptime_seconds() -> None:
    started_at = datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC)
    now = datetime(2026, 4, 30, 12, 1, 5, tzinfo=UTC)

    assert process_uptime_seconds(started_at, now=now) == 65


def test_format_uptime_report() -> None:
    started_at = datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC)
    now = datetime(2026, 4, 30, 12, 1, 5, tzinfo=UTC)

    report = format_uptime_report(
        process_started_at=started_at,
        host_uptime_seconds=93_784,
        now=now,
    )

    assert "🤖 MarcBot uptime" in report
    assert "Host uptime: 1 day, 02 hours, 03 minutes, 04 seconds" in report
    assert "Process uptime: 01 minute, 05 seconds" in report
