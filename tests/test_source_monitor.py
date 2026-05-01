from datetime import UTC, datetime
from pathlib import Path

from marcbot.source_config import SourceConfig, SourceDefinition
from marcbot.source_monitor import build_source_monitor_report, write_source_monitor_report


def test_build_source_monitor_report_includes_scaffold_status() -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
    config = SourceConfig(path=Path("/srv/marcbot/config/sources.toml"), exists=False, sources=())

    report = build_source_monitor_report(now=now, config=config)

    assert "# MarcBot Source Monitor - 2026-05-01" in report
    assert "MarcBot version:" in report
    assert "Source monitor config integration is installed." in report
    assert "No sources were fetched in this version." in report


def test_build_source_monitor_report_handles_empty_config() -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
    config = SourceConfig(path=Path("/srv/marcbot/config/sources.toml"), exists=False, sources=())

    report = build_source_monitor_report(now=now, config=config)

    assert "## Configured sources" in report
    assert "Config exists: false" in report
    assert "Configured sources: 0" in report
    assert "No sources are configured." in report


def test_build_source_monitor_report_lists_configured_sources() -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
    config = SourceConfig(
        path=Path("/srv/marcbot/config/sources.toml"),
        exists=True,
        sources=(
            SourceDefinition(
                name="openai-news",
                kind="web_page",
                url="https://openai.com/news/",
                enabled=True,
            ),
            SourceDefinition(
                name="example-disabled",
                kind="github_releases",
                url="https://github.com/example/project/releases",
                enabled=False,
            ),
        ),
    )

    report = build_source_monitor_report(now=now, config=config)

    assert "Config exists: true" in report
    assert "Configured sources: 2" in report
    assert "- openai-news" in report
    assert "  - kind: web_page" in report
    assert "  - state: enabled" in report
    assert "  - url: https://openai.com/news/" in report
    assert "- example-disabled" in report
    assert "  - kind: github_releases" in report
    assert "  - state: disabled" in report


def test_write_source_monitor_report_creates_report(tmp_path: Path) -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)

    result = write_source_monitor_report(reports_dir=tmp_path, now=now)

    assert result.path == tmp_path / "source-monitor-2026-05-01-123000.md"
    assert result.path.exists()
    assert result.message == f"Source monitor report written: {result.path}"
    assert "# MarcBot Source Monitor - 2026-05-01" in result.path.read_text(
        encoding="utf-8"
    )
