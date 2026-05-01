"""Tests for local MarcBot reports."""

from datetime import UTC, datetime

from marcbot import __version__
from marcbot.reports import build_daily_status_report, write_daily_status_report


def test_build_daily_status_report_contains_expected_headings() -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)

    report = build_daily_status_report(now=now)

    assert "# MarcBot Daily Status - 2026-05-01" in report
    assert f"MarcBot version: {__version__}" in report
    assert "## Runtime" in report
    assert "## Disk" in report
    assert "## Service" in report
    assert "## Git" in report
    assert "## Backup" in report
    assert "## Notes" in report
    assert "locally generated report scaffold" in report


def test_write_daily_status_report_writes_expected_file(tmp_path) -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)

    result = write_daily_status_report(reports_dir=tmp_path, now=now)

    assert result.path == tmp_path / "daily-status-2026-05-01.md"
    assert result.path.is_file()
    assert "Daily status report written:" in result.message
    assert "# MarcBot Daily Status - 2026-05-01" in result.path.read_text(encoding="utf-8")
