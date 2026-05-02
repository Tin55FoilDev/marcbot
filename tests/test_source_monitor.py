from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

from marcbot.source_config import SourceConfig, SourceDefinition
from marcbot.source_monitor import (
    SourceFetchResult,
    apply_change_detection,
    build_source_monitor_report,
    build_source_monitor_state,
    classify_source_change,
    extract_html_title,
    fetch_configured_sources,
    fetch_source_metadata,
    load_source_monitor_state,
    source_monitor_state_path,
    summarize_fetch_results,
    write_source_monitor_report,
)


def make_source(
    name: str = "openai-news",
    kind: str = "web_page",
    url: str = "https://openai.com/news/",
    enabled: bool = True,
) -> SourceDefinition:
    return SourceDefinition(name=name, kind=kind, url=url, enabled=enabled)


def test_source_monitor_state_path_uses_project_layout() -> None:
    assert source_monitor_state_path("ai") == Path(
        "/srv/marcbot/workspace/source-projects/ai/state/source-monitor-state.json"
    )


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


def test_classify_source_change_marks_new_when_missing_previous() -> None:
    result = SourceFetchResult(
        source=make_source(),
        fetched=True,
        status=200,
        bytes_read=100,
        error=None,
        title="OpenAI News",
    )

    assert classify_source_change(result, None) == "new"


def test_classify_source_change_marks_unchanged_when_metadata_matches() -> None:
    result = SourceFetchResult(
        source=make_source(),
        fetched=True,
        status=200,
        bytes_read=100,
        error=None,
        title="OpenAI News",
    )
    previous = {
        "status": 200,
        "title": "OpenAI News",
        "error": None,
    }

    assert classify_source_change(result, previous) == "unchanged"


def test_classify_source_change_marks_changed_when_title_changes() -> None:
    result = SourceFetchResult(
        source=make_source(),
        fetched=True,
        status=200,
        bytes_read=100,
        error=None,
        title="New Title",
    )
    previous = {
        "status": 200,
        "title": "Old Title",
        "error": None,
    }

    assert classify_source_change(result, previous) == "changed"


def test_apply_change_detection_annotates_each_result() -> None:
    openai = SourceFetchResult(
        source=make_source(),
        fetched=True,
        status=200,
        bytes_read=100,
        error=None,
        title="OpenAI News",
    )
    anthropic = SourceFetchResult(
        source=make_source(name="anthropic-news", url="https://www.anthropic.com/news"),
        fetched=True,
        status=200,
        bytes_read=100,
        error=None,
        title="Anthropic News",
    )
    previous_state = {
        "sources": {
            "openai-news": {
                "status": 200,
                "title": "OpenAI News",
                "error": None,
            },
            "anthropic-news": {
                "status": 200,
                "title": "Old Anthropic Title",
                "error": None,
            },
        },
    }

    annotated = apply_change_detection((openai, anthropic), previous_state)

    assert annotated[0].change_state == "unchanged"
    assert annotated[1].change_state == "changed"


def test_summarize_fetch_results_counts_states_and_errors() -> None:
    results = (
        SourceFetchResult(
            source=make_source(name="new-source"),
            fetched=True,
            status=200,
            bytes_read=100,
            title="New",
            change_state="new",
        ),
        SourceFetchResult(
            source=make_source(name="changed-source"),
            fetched=True,
            status=200,
            bytes_read=100,
            title="Changed",
            change_state="changed",
        ),
        SourceFetchResult(
            source=make_source(name="unchanged-source"),
            fetched=True,
            status=200,
            bytes_read=100,
            title="Unchanged",
            change_state="unchanged",
        ),
        SourceFetchResult(
            source=make_source(name="errored-source"),
            fetched=True,
            status=None,
            bytes_read=0,
            error="timeout",
            change_state="changed",
        ),
        SourceFetchResult(
            source=make_source(name="disabled-source", enabled=False),
            fetched=False,
            status=None,
            bytes_read=0,
            error="disabled",
            change_state="unchanged",
        ),
    )

    summary = summarize_fetch_results(results)

    assert summary == {
        "total": 5,
        "new": 1,
        "changed": 2,
        "unchanged": 2,
        "errored": 1,
    }


def test_build_source_monitor_state_contains_metadata_only() -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
    result = SourceFetchResult(
        source=make_source(),
        fetched=True,
        status=200,
        bytes_read=100,
        error=None,
        title="OpenAI News",
        change_state="new",
    )

    state = build_source_monitor_state("ai", (result,), now)

    assert state["version"] == 1
    assert state["project"] == "ai"
    assert state["sources"]["openai-news"] == {
        "kind": "web_page",
        "url": "https://openai.com/news/",
        "fetched": True,
        "status": 200,
        "title": "OpenAI News",
        "error": None,
    }


def test_load_source_monitor_state_returns_empty_for_missing_file(tmp_path: Path) -> None:
    assert load_source_monitor_state(tmp_path / "missing.json") == {}


def test_load_source_monitor_state_returns_empty_for_invalid_json(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text("{bad json", encoding="utf-8")

    assert load_source_monitor_state(state_path) == {}


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
    assert (
        "Source monitor bounded fetch metadata, title extraction, "
        "and change detection are installed."
    ) in report


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
            change_state="new",
        ),
        SourceFetchResult(
            source=disabled,
            fetched=False,
            status=None,
            bytes_read=0,
            error="disabled",
            title=None,
            change_state="unchanged",
        ),
    )

    report = build_source_monitor_report(
        now=now,
        config=config,
        fetch_results=fetch_results,
        state_path=Path("/tmp/state.json"),
    )

    assert "State path: /tmp/state.json" in report
    assert "## Summary" in report
    assert "Total sources checked: 2" in report
    assert "New: 1" in report
    assert "Changed: 0" in report
    assert "Unchanged: 1" in report
    assert "Errored: 0" in report
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
    assert "  - change: new" in report
    assert "  - error: none" in report
    assert "- example-disabled" in report
    assert "  - state: disabled" in report
    assert "  - fetched: false" in report
    assert "  - status: n/a" in report
    assert "  - title: n/a" in report
    assert "  - change: unchanged" in report
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
    body = b"<html><head><title>Example Title</title></head></html>"
    response.status = 200
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



def test_build_source_monitor_report_includes_observations() -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
    config = SourceConfig(
        project_name="ai",
        path=Path("/tmp/sources.toml"),
        exists=True,
        sources=(
            make_source(name="openai-news"),
            make_source(name="anthropic-news", url="https://www.anthropic.com/news"),
            make_source(name="errored-source", url="https://example.com/error"),
            make_source(name="unchanged-source", url="https://example.com/unchanged"),
        ),
    )
    fetch_results = (
        SourceFetchResult(
            source=make_source(name="openai-news"),
            fetched=True,
            status=200,
            bytes_read=1234,
            title="OpenAI News",
            error=None,
            change_state="new",
        ),
        SourceFetchResult(
            source=make_source(name="anthropic-news", url="https://www.anthropic.com/news"),
            fetched=True,
            status=200,
            bytes_read=2345,
            title="Anthropic News",
            error=None,
            change_state="changed",
        ),
        SourceFetchResult(
            source=make_source(name="errored-source", url="https://example.com/error"),
            fetched=False,
            status=None,
            bytes_read=0,
            title=None,
            error="timeout",
            change_state="changed",
        ),
        SourceFetchResult(
            source=make_source(name="unchanged-source", url="https://example.com/unchanged"),
            fetched=True,
            status=200,
            bytes_read=3456,
            title="Unchanged News",
            error=None,
            change_state="unchanged",
        ),
    )

    report = build_source_monitor_report(
        now=now,
        config=config,
        fetch_results=fetch_results,
        state_path=Path("/tmp/state.json"),
    )

    assert "## Observations" in report
    assert "Attention:" in report
    assert "- openai-news: new source observed; title: OpenAI News" in report
    assert "- anthropic-news: metadata changed; title: Anthropic News" in report
    assert "- errored-source: error: timeout" in report
    assert "unchanged-source: metadata changed" not in report


def test_build_source_monitor_report_observations_quiet_when_unchanged_only() -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
    config = SourceConfig(
        project_name="ai",
        path=Path("/tmp/sources.toml"),
        exists=True,
        sources=(make_source(name="openai-news"),),
    )
    fetch_results = (
        SourceFetchResult(
            source=make_source(name="openai-news"),
            fetched=True,
            status=200,
            bytes_read=1234,
            title="OpenAI News",
            error=None,
            change_state="unchanged",
        ),
    )

    report = build_source_monitor_report(
        now=now,
        config=config,
        fetch_results=fetch_results,
        state_path=Path("/tmp/state.json"),
    )

    assert "## Observations" in report
    assert "No new, changed, or errored sources were detected." in report

def test_write_source_monitor_report_creates_project_report_and_state(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
    state_path = tmp_path / "state" / "source-monitor-state.json"

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
                reports_dir=tmp_path / "reports",
                state_path=state_path,
                now=now,
            )

    assert result.path == tmp_path / "reports/source-monitor-2026-05-01-123000.md"
    assert result.path.exists()
    assert state_path.exists()
    assert result.message == f"Source monitor report written: {result.path}"
    assert "# MarcBot Source Monitor - ai - 2026-05-01" in result.path.read_text(
        encoding="utf-8"
    )
