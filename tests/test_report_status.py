"""Tests for MarcBot report status."""

from datetime import UTC, datetime, timedelta

from marcbot.report_status import format_report_status_message


def test_report_status_reports_missing_directory(tmp_path) -> None:
    missing = tmp_path / "missing"

    message = format_report_status_message(
        reports_dir=missing,
        now=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        timer_state_func=lambda: "enabled",
    )

    assert "🤖 MarcBot report status" in message
    assert "Latest daily status report: none" in message
    assert "reports directory is missing" in message


def test_report_status_reports_no_reports(tmp_path) -> None:
    message = format_report_status_message(
        reports_dir=tmp_path,
        now=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        timer_state_func=lambda: "enabled",
    )

    assert "Latest daily status report: none" in message
    assert "marcbot-daily-status-report.timer enabled" in message
    assert "no daily status reports found" in message


def test_report_status_reports_latest_file(tmp_path) -> None:
    old = tmp_path / "daily-status-2026-04-30.md"
    latest = tmp_path / "daily-status-2026-05-01.md"

    old.write_text("old\n", encoding="utf-8")
    latest.write_text("# MarcBot Daily Status\n", encoding="utf-8")

    latest_time = datetime(2026, 5, 1, 11, 0, tzinfo=UTC)
    old_time = latest_time - timedelta(days=1)

    old_ts = old_time.timestamp()
    latest_ts = latest_time.timestamp()

    old.touch()
    latest.touch()

    import os

    os.utime(old, (old_ts, old_ts))
    os.utime(latest, (latest_ts, latest_ts))

    message = format_report_status_message(
        reports_dir=tmp_path,
        now=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        timer_state_func=lambda: "enabled",
    )

    assert "Latest daily status report: daily-status-2026-05-01.md" in message
    assert "Size:" in message
    assert "Age: 1 hour" in message
    assert "marcbot-daily-status-report.timer enabled" in message
    assert "Overall: healthy" in message


def test_report_status_warns_when_stale(tmp_path) -> None:
    latest = tmp_path / "daily-status-2026-04-29.md"
    latest.write_text("stale\n", encoding="utf-8")

    latest_time = datetime(2026, 4, 29, 12, 0, tzinfo=UTC)
    latest_ts = latest_time.timestamp()

    import os

    os.utime(latest, (latest_ts, latest_ts))

    message = format_report_status_message(
        reports_dir=tmp_path,
        now=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        timer_state_func=lambda: "enabled",
    )

    assert "warning - latest report is older than 36 hours" in message


def test_report_status_warns_when_timer_not_enabled(tmp_path) -> None:
    latest = tmp_path / "daily-status-2026-05-01.md"
    latest.write_text("ok\n", encoding="utf-8")

    latest_time = datetime(2026, 5, 1, 11, 0, tzinfo=UTC)
    latest_ts = latest_time.timestamp()

    import os

    os.utime(latest, (latest_ts, latest_ts))

    message = format_report_status_message(
        reports_dir=tmp_path,
        now=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        timer_state_func=lambda: "disabled",
    )

    assert "marcbot-daily-status-report.timer disabled" in message
    assert "warning - report timer is not enabled" in message
