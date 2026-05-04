from pathlib import Path

from marcbot.source_status import (
    extract_source_report_rss_highlights,
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


def test_extract_source_report_summary_returns_summary_and_observations() -> None:
    report = """# MarcBot Source Monitor - ai - 2026-05-01

Generated: 2026-05-01T12:30:00+00:00

## Summary

Total sources checked: 4
New: 0
Changed: 1
Unchanged: 3
Errored: 0

## Observations

Attention:
- openai-news: metadata changed; title: OpenAI News

## Configured sources

- openai-news
"""

    summary = extract_source_report_summary(report)

    assert summary == """## Summary

Total sources checked: 4
New: 0
Changed: 1
Unchanged: 3
Errored: 0

## Observations

Attention:
- openai-news: metadata changed; title: OpenAI News"""


def test_extract_source_report_summary_returns_none_when_missing() -> None:
    assert extract_source_report_summary("# No summary\n") is None



def test_extract_source_report_rss_highlights_returns_latest_items() -> None:
    report = """# MarcBot Source Monitor - ai - 2026-05-01

## Fetch results

- openai-news
  - kind: rss_feed
  - url: https://openai.com/news/rss.xml
  - fetched: true
  - status: 200
  - bytes_read: 1234
  - title: n/a
  - feed_title: OpenAI News
  - latest_item_title: New model release
  - latest_item_link: https://openai.com/news/example/
  - latest_item_published: Sat, 02 May 2026 11:30:00 GMT
  - change: unchanged
  - error: none
- anthropic-news
  - kind: web_page
  - title: Anthropic News
  - change: unchanged
  - error: none
"""

    highlights = extract_source_report_rss_highlights(report)

    assert highlights == """## RSS latest items

- openai-news: New model release
  published: Sat, 02 May 2026 11:30:00 GMT"""


def test_extract_source_report_rss_highlights_returns_none_without_rss_items() -> None:
    report = """# MarcBot Source Monitor - ai - 2026-05-01

## Fetch results

- anthropic-news
  - kind: web_page
  - title: Anthropic News
  - change: unchanged
  - error: none
"""

    assert extract_source_report_rss_highlights(report) is None

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

## Observations

Attention:
- openai-news: metadata changed; title: OpenAI News

## Fetch results

- openai-news
  - kind: rss_feed
  - title: n/a
  - feed_title: OpenAI News
  - latest_item_title: New model release
  - latest_item_link: https://openai.com/news/example/
  - latest_item_published: Sat, 02 May 2026 11:30:00 GMT
  - change: unchanged
  - error: none
""",
        encoding="utf-8",
    )

    message = format_source_status_message(reports_dir=tmp_path)

    assert "Project: ai" in message
    assert f"Report: {report}" in message
    assert "Generated: 2026-05-01T13:00:00+00:00" in message
    assert "## Summary" in message
    assert "Changed: 1" in message
    assert "## Observations" in message
    assert "openai-news: metadata changed" in message
    assert "## RSS latest items" in message
    assert "openai-news: New model release" in message
    assert "published: Sat, 02 May 2026 11:30:00 GMT" in message
    assert "## Fetch results" not in message


def test_format_source_status_message_handles_invalid_project_name() -> None:
    message = format_source_status_message(project_name="../bad")

    assert "Status: invalid project name" in message
    assert "MBOT-SOURCE-" in message


def test_find_latest_source_monitor_summary_returns_newest_file(tmp_path) -> None:
    from marcbot.source_status import find_latest_source_monitor_summary

    older = tmp_path / "source-monitor-2026-05-01-120000.summary.md"
    newer = tmp_path / "source-monitor-2026-05-01-130000.summary.md"
    unrelated = tmp_path / "source-monitor-2026-05-01-140000.md"

    older.write_text("older", encoding="utf-8")
    newer.write_text("newer", encoding="utf-8")
    unrelated.write_text("not a summary", encoding="utf-8")

    assert find_latest_source_monitor_summary(summaries_dir=tmp_path) == newer


def test_format_source_monitor_cli_status_reports_saved_artifacts(
    tmp_path,
    monkeypatch,
) -> None:
    import marcbot.source_status as source_status
    from marcbot.source_config import SourceConfig

    config_path = tmp_path / "config" / "sources.toml"
    reports_dir = tmp_path / "reports"
    summaries_dir = tmp_path / "summaries"
    report_path = reports_dir / "source-monitor-2026-05-02-120000.md"
    summary_path = summaries_dir / "source-monitor-2026-05-02-120000.summary.md"

    reports_dir.mkdir(parents=True)
    summaries_dir.mkdir(parents=True)
    config_path.parent.mkdir(parents=True)
    config_path.write_text("[[sources]]\n", encoding="utf-8")

    report_path.write_text(
        """# Source Monitor Report

Generated: 2026-05-02T12:00:00+00:00

## Summary

- Checked 2 sources.

## Fetch results

- example
  - kind: rss_feed
  - status: ok
  - change: changed
  - error: n/a
- second
  - kind: rss_feed
  - status: error
  - change: n/a
  - error: timeout
""",
        encoding="utf-8",
    )
    summary_path.write_text("# Summary\n\nSaved LLM summary.\n", encoding="utf-8")

    monkeypatch.setattr(
        source_status,
        "load_source_config",
        lambda project_name: SourceConfig(
            path=config_path,
            exists=True,
            sources=(),
            project_name=project_name,
        ),
    )

    output = source_status.format_source_monitor_cli_status(
        "ai",
        reports_dir=reports_dir,
        summaries_dir=summaries_dir,
    )

    assert "MarcBot source monitor status" in output
    assert "Project: ai" in output
    assert "Config: valid" in output
    assert f"Config path: {config_path}" in output
    assert f"Reports dir: {reports_dir}" in output
    assert f"Summaries dir: {summaries_dir}" in output
    assert f"Latest report: {report_path}" in output
    assert f"Latest summary: {summary_path}" in output
    assert "Generated: 2026-05-02T12:00:00+00:00" in output
    assert "Report age:" in output
    assert "Summary age:" in output
    assert "Summary freshness:" in output
    assert "Report state: changed sources: 1; errors: 1" in output


def test_format_elapsed_since_uses_compact_human_units() -> None:
    from datetime import UTC, datetime, timedelta

    from marcbot.source_status import _format_elapsed_since

    now = datetime(2026, 5, 3, 12, 0, 0, tzinfo=UTC)

    assert _format_elapsed_since(now - timedelta(seconds=20), now) == (
        "less than 1 minute ago"
    )
    assert _format_elapsed_since(now - timedelta(minutes=1), now) == "1 minute ago"
    assert _format_elapsed_since(now - timedelta(minutes=15), now) == "15 minutes ago"
    assert _format_elapsed_since(now - timedelta(hours=1), now) == "1 hour ago"
    assert _format_elapsed_since(now - timedelta(hours=7), now) == "7 hours ago"
    assert _format_elapsed_since(now - timedelta(days=3), now) == "3 days ago"
