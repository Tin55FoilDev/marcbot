"""Tests for latest MarcBot report lookup."""

import os
from datetime import UTC, datetime, timedelta

from marcbot.latest_report import (
    find_latest_daily_status_report,
    validate_latest_daily_status_report,
)


def test_find_latest_daily_status_report_returns_none_for_missing_directory(tmp_path) -> None:
    missing = tmp_path / "missing"

    assert find_latest_daily_status_report(reports_dir=missing) is None


def test_find_latest_daily_status_report_ignores_non_matching_files(tmp_path) -> None:
    (tmp_path / "notes.md").write_text("notes\n", encoding="utf-8")

    assert find_latest_daily_status_report(reports_dir=tmp_path) is None


def test_find_latest_daily_status_report_returns_newest_matching_file(tmp_path) -> None:
    now = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)

    old = tmp_path / "daily-status-2026-04-30.md"
    new = tmp_path / "daily-status-2026-05-01.md"

    old.write_text("old\n", encoding="utf-8")
    new.write_text("new\n", encoding="utf-8")

    old_ts = (now - timedelta(days=1)).timestamp()
    new_ts = now.timestamp()

    os.utime(old, (old_ts, old_ts))
    os.utime(new, (new_ts, new_ts))

    assert find_latest_daily_status_report(reports_dir=tmp_path) == new


def test_validate_latest_daily_status_report_reports_missing_directory(tmp_path) -> None:
    result = validate_latest_daily_status_report(reports_dir=tmp_path / "missing")

    assert result.ok is False
    assert result.path is None
    assert "Reports directory is missing" in result.message


def test_validate_latest_daily_status_report_reports_no_reports(tmp_path) -> None:
    result = validate_latest_daily_status_report(reports_dir=tmp_path)

    assert result.ok is False
    assert result.path is None
    assert "No daily status reports found" in result.message


def test_validate_latest_daily_status_report_returns_latest_path(tmp_path) -> None:
    report = tmp_path / "daily-status-2026-05-01.md"
    report.write_text("report\n", encoding="utf-8")

    result = validate_latest_daily_status_report(reports_dir=tmp_path)

    assert result.ok is True
    assert result.path == report
    assert "Latest daily status report: daily-status-2026-05-01.md" in result.message
