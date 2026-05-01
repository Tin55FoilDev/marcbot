"""Tests for MarcBot source monitor reports."""

from datetime import UTC, datetime

from marcbot import __version__
from marcbot.source_monitor import build_source_monitor_report, write_source_monitor_report


def test_build_source_monitor_report_contains_expected_scaffold_text() -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)

    report = build_source_monitor_report(now=now)

    assert "# MarcBot Source Monitor - 2026-05-01" in report
    assert f"MarcBot version: {__version__}" in report
    assert "## Status" in report
    assert "Source monitor scaffold is installed." in report
    assert "No sources were checked in this scaffold version." in report
    assert "## Next steps" in report


def test_write_source_monitor_report_writes_timestamped_file(tmp_path) -> None:
    now = datetime(2026, 5, 1, 12, 30, 45, tzinfo=UTC)

    result = write_source_monitor_report(reports_dir=tmp_path, now=now)

    assert result.path == tmp_path / "source-monitor-2026-05-01-123045.md"
    assert result.path.is_file()
    assert "Source monitor report written:" in result.message
    assert "# MarcBot Source Monitor - 2026-05-01" in result.path.read_text(
        encoding="utf-8",
    )
