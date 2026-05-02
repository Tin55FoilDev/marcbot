from pathlib import Path

from marcbot.source_status import (
    extract_source_report_summary,
    find_latest_source_monitor_report,
    format_source_status_message,
)


def test_find_latest_source_monitor_report_returns_latest_by_name(tmp_path: Path) -> None:
    older = tmp_path / "source-monitor-2026-05-01-120000.md"
    newer = tmp_path / "source-monitor-2026-05-01-130000.md"
    older.write_text("older", encoding="utf-8")
    newer.write_text("newer", encoding="utf-8")

    assert find_latest_source_monitor_report(reports_dir=tmp_path) == newer


def test_find_latest_source_monitor_report_returns_none_when_missing(
    tmp_path: Path,
) -> None:
    assert find_latest_source_monitor_report(reports_dir=tmp_path) is None


def test_extract_source_report_summary_returns_summary_section_only() -> None:
    report = """# MarcBot Source Monitor - ai - 2026-05-01

Generated: 2026-05-01T12:30:00+00:00

## Summary

Total sources checked: 4
New: 0
Changed: 1
Unchanged: 3
Errored: 0

## Configured sources

- openai-news
"""

    summary = extract_source_report_summary(report)

    assert summary == """## Summary

Total sources checked: 4
New: 0
Changed: 1
Unchanged: 3
Errored: 0"""


def test_extract_source_report_summary_returns_none_when_missing() -> None:
    assert extract_source_report_summary("# No summary\n") is None


def test_format_source_status_message_handles_missing_report(tmp_path: Path) -> None:
    message = format_source_status_message(reports_dir=tmp_path)

    assert "🤖 MarcBot source monitor report status" in message
    assert "Status: no local report found" in message
    assert f"Expected reports dir: {tmp_path}" in message


def test_format_source_status_message_includes_latest_summary(tmp_path: Path) -> None:
    report = tmp_path / "source-monitor-2026-05-01-130000.md"
    report.write_text(
        """# MarcBot Source Monitor - ai - 2026-05-01

Generated: 2026-05-01T13:00:00+00:00

## Summary

Total sources checked: 4
New: 0
Changed: 1
Unchanged: 3
Errored: 0

## Fetch results

- openai-news
  - title: OpenAI News
""",
        encoding="utf-8",
    )

    message = format_source_status_message(reports_dir=tmp_path)

    assert "Project: ai" in message
    assert f"Report: {report}" in message
    assert "Generated: 2026-05-01T13:00:00+00:00" in message
    assert "## Summary" in message
    assert "Changed: 1" in message
    assert "## Fetch results" not in message


def test_format_source_status_message_handles_invalid_project_name() -> None:
    message = format_source_status_message(project_name="../bad")

    assert "Status: invalid project name" in message
    assert "MBOT-SOURCE-" in message
