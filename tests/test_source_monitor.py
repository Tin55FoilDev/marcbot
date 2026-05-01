from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

from marcbot.source_config import SourceConfig, SourceDefinition
from marcbot.source_monitor import (
    SourceFetchResult,
    build_source_monitor_report,
    extract_html_title,
    fetch_configured_sources,
    fetch_source_metadata,
    write_source_monitor_report,
)


def make_source(
    name: str = "openai-news",
    kind: str = "web_page",
    url: str = "https://openai.com/news/",
    enabled: bool = True,
) -> SourceDefinition:
    return SourceDefinition(name=name, kind=kind, url=url, enabled=enabled)


def test_extract_html_title_returns_normalized_title() -> None:
    title = extract_html_title(
        b"""
<html>
<head>
<title>
  Example
  News
</title>
</head>
<body>Hello</body>
</html>
"""
    )

    assert title == "Example News"


def test_extract_html_title_returns_none_when_missing() -> None:
    assert extract_html_title(b"<html><body>No title</body></html>") is None


def test_build_source_monitor_report_includes_project_status() -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
    config = SourceConfig(
        path=Path("/srv/marcbot/config/source-projects/ai/sources.toml"),
        exists=False,
        sources=(),
        project_name="ai",
    )

    report = build_source_monitor_report(now=now, config=config, fetch_results=())

    assert "# MarcBot Source Monitor - ai - 2026-05-01" in report
    assert "MarcBot version:" in report
    assert "Project: ai" in report
    assert "Source monitor bounded fetch metadata and title extraction are installed." in report


def test_build_source_monitor_report_handles_empty_config() -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
    config = SourceConfig(
        path=Path("/srv/marcbot/config/source-projects/ai/sources.toml"),
        exists=False,
        sources=(),
        project_name="ai",
    )

    report = build_source_monitor_report(now=now, config=config, fetch_results=())

    assert "## Configured sources" in report
    assert "Project: ai" in report
    assert "Config exists: false" in report
    assert "Configured sources: 0" in report
    assert "No sources are configured." in report
    assert "## Fetch results" in report
    assert "No sources were fetched." in report


def test_build_source_monitor_report_lists_configured_sources_and_fetch_results() -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
    source = make_source()
    disabled = make_source(
        name="example-disabled",
        kind="github_releases",
        url="https://github.com/example/project/releases",
        enabled=False,
    )
    config = SourceConfig(
        path=Path("/srv/marcbot/config/source-projects/ai/sources.toml"),
        exists=True,
        sources=(source, disabled),
        project_name="ai",
    )
    fetch_results = (
        SourceFetchResult(
            source=source,
            fetched=True,
            status=200,
            bytes_read=1234,
            error=None,
            title="OpenAI News",
        ),
        SourceFetchResult(
            source=disabled,
            fetched=False,
            status=None,
            bytes_read=0,
            error="disabled",
            title=None,
        ),
    )

    report = build_source_monitor_report(
        now=now,
        config=config,
        fetch_results=fetch_results,
    )

    assert "Config exists: true" in report
    assert "Configured sources: 2" in report
    assert "- openai-news" in report
    assert "  - kind: web_page" in report
    assert "  - state: enabled" in report
    assert "  - url: https://openai.com/news/" in report
    assert "## Fetch results" in report
    assert "  - fetched: true" in report
    assert "  - status: 200" in report
    assert "  - bytes_read: 1234" in report
    assert "  - title: OpenAI News" in report
    assert "  - error: none" in report
    assert "- example-disabled" in report
    assert "  - state: disabled" in report
    assert "  - fetched: false" in report
    assert "  - status: n/a" in report
    assert "  - title: n/a" in report
    assert "  - error: disabled" in report


def test_fetch_source_metadata_skips_disabled_source() -> None:
    source = make_source(enabled=False)

    result = fetch_source_metadata(source)

    assert result.source == source
    assert result.fetched is False
    assert result.status is None
    assert result.bytes_read == 0
    assert result.error == "disabled"
    assert result.title is None


def test_fetch_source_metadata_captures_success_metadata_and_title() -> None:
    source = make_source()
    response = Mock()
    response.status = 200
    body = b"<html><head><title>Example Title</title></head></html>"
    response.read.return_value = body
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=None)

    with patch("marcbot.source_monitor.urlopen", return_value=response) as mock_urlopen:
        result = fetch_source_metadata(source)

    assert result.source == source
    assert result.fetched is True
    assert result.status == 200
    assert result.bytes_read == len(body)
    assert result.error is None
    assert result.title == "Example Title"
    mock_urlopen.assert_called_once()


def test_fetch_source_metadata_caps_byte_count() -> None:
    source = make_source()
    response = Mock()
    response.status = 200
    response.read.return_value = b"x" * ((256 * 1024) + 1)
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=None)

    with patch("marcbot.source_monitor.urlopen", return_value=response):
        result = fetch_source_metadata(source)

    assert result.bytes_read == 256 * 1024


def test_fetch_configured_sources_returns_one_result_per_source() -> None:
    source = make_source()
    disabled = make_source(name="disabled-source", enabled=False)
    config = SourceConfig(
        path=Path("/srv/marcbot/config/source-projects/ai/sources.toml"),
        exists=True,
        sources=(source, disabled),
        project_name="ai",
    )

    with patch("marcbot.source_monitor.fetch_source_metadata") as mock_fetch:
        mock_fetch.side_effect = [
            SourceFetchResult(source=source, fetched=True, status=200, bytes_read=10),
            SourceFetchResult(
                source=disabled,
                fetched=False,
                status=None,
                bytes_read=0,
                error="disabled",
            ),
        ]
        results = fetch_configured_sources(config)

    assert len(results) == 2
    assert results[0].source == source
    assert results[1].source == disabled


def test_write_source_monitor_report_creates_project_report(tmp_path: Path) -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)

    with patch("marcbot.source_monitor.load_source_config") as mock_load_config:
        with patch("marcbot.source_monitor.fetch_configured_sources") as mock_fetch:
            config = SourceConfig(
                path=Path("/srv/marcbot/config/source-projects/ai/sources.toml"),
                exists=False,
                sources=(),
                project_name="ai",
            )
            mock_load_config.return_value = config
            mock_fetch.return_value = ()

            result = write_source_monitor_report(
                project_name="ai",
                reports_dir=tmp_path,
                now=now,
            )

    assert result.path == tmp_path / "source-monitor-2026-05-01-123000.md"
    assert result.path.exists()
    assert result.message == f"Source monitor report written: {result.path}"
    assert "# MarcBot Source Monitor - ai - 2026-05-01" in result.path.read_text(
        encoding="utf-8"
    )
