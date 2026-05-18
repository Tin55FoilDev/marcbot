from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from marcbot.weather_status import format_weather_status_message


def test_format_weather_status_reports_missing_directory(tmp_path: Path) -> None:
    message = format_weather_status_message(reports_dir=tmp_path / "missing")

    assert "MarcBot weather report" in message
    assert "Latest report: missing" in message
    assert "Status: reports directory not found" in message
    assert "Provider contact: no" in message


def test_format_weather_status_reports_no_reports(tmp_path: Path) -> None:
    message = format_weather_status_message(reports_dir=tmp_path)

    assert "Latest report: none" in message
    assert "Status: no weather reports found" in message
    assert "Provider contact: no" in message


def test_format_weather_status_reports_latest_report(tmp_path: Path) -> None:
    older = tmp_path / "weather-report-2026-05-17-071500.md"
    newer = tmp_path / "weather-report-2026-05-18-071500.md"
    older.write_text("older", encoding="utf-8")
    newer.write_text("newer", encoding="utf-8")

    older_modified = datetime(2026, 5, 17, 11, 15, tzinfo=UTC).timestamp()
    newer_modified = datetime(2026, 5, 18, 11, 15, tzinfo=UTC).timestamp()
    os.utime(older, (older_modified, older_modified))
    os.utime(newer, (newer_modified, newer_modified))

    message = format_weather_status_message(reports_dir=tmp_path)

    assert "Latest report: weather-report-2026-05-18-071500.md" in message
    assert "Latest modified: 2026-05-18T11:15:00+00:00" in message
    assert "Status: latest weather report found" in message
    assert "Timer: see /timer_status" in message
    assert "Provider contact: no" in message
