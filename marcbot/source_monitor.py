"""Source monitor report generation."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from marcbot import __version__
from marcbot.source_config import (
    DEFAULT_SOURCE_PROJECT_NAME,
    SourceConfig,
    SourceDefinition,
    load_source_config,
    source_reports_dir,
)

FETCH_TIMEOUT_SECONDS = 10
MAX_FETCH_BYTES = 256 * 1024
USER_AGENT = f"MarcBot/{__version__} source-monitor"
SOURCE_MONITOR_STATE_FILENAME = "source-monitor-state.json"


class _TitleParser(HTMLParser):
    """Tiny HTML title parser for bounded source monitor responses."""

    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        _attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)

    @property
    def title(self) -> str | None:
        normalized = " ".join(" ".join(self._title_parts).split())
        return normalized or None


@dataclass(frozen=True)
class SourceFetchResult:
    """Bounded fetch metadata for one configured source."""

    source: SourceDefinition
    fetched: bool
    status: int | None
    bytes_read: int
    error: str | None = None
    title: str | None = None
    change_state: str | None = None


@dataclass(frozen=True)
class SourceMonitorResult:
    """Result of writing a source monitor report."""

    path: Path
    message: str


def source_monitor_state_path(project_name: str = DEFAULT_SOURCE_PROJECT_NAME) -> Path:
    """Return the deterministic state path for a source monitor project."""
    return source_reports_dir(project_name).parent / "state" / SOURCE_MONITOR_STATE_FILENAME


def extract_html_title(data: bytes) -> str | None:
    """Extract a basic HTML title from already-bounded response bytes."""
    if not data:
        return None

    parser = _TitleParser()
    parser.feed(data.decode("utf-8", errors="replace"))
    parser.close()
    return parser.title


def fetch_source_metadata(source: SourceDefinition) -> SourceFetchResult:
    """Fetch bounded metadata for one enabled allowlisted source."""
    if not source.enabled:
        return SourceFetchResult(
            source=source,
            fetched=False,
            status=None,
            bytes_read=0,
            error="disabled",
        )

    request = Request(
        source.url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            data = response.read(MAX_FETCH_BYTES + 1)
            bounded_data = data[:MAX_FETCH_BYTES]
            return SourceFetchResult(
                source=source,
                fetched=True,
                status=response.status,
                bytes_read=len(bounded_data),
                error=None,
                title=extract_html_title(bounded_data),
            )
    except HTTPError as exc:
        return SourceFetchResult(
            source=source,
            fetched=True,
            status=exc.code,
            bytes_read=0,
            error=f"http error: {exc.code}",
        )
    except URLError as exc:
        return SourceFetchResult(
            source=source,
            fetched=True,
            status=None,
            bytes_read=0,
            error=f"url error: {exc.reason}",
        )
    except TimeoutError:
        return SourceFetchResult(
            source=source,
            fetched=True,
            status=None,
            bytes_read=0,
            error="timeout",
        )
    except OSError as exc:
        return SourceFetchResult(
            source=source,
            fetched=True,
            status=None,
            bytes_read=0,
            error=f"os error: {exc.strerror or exc.__class__.__name__}",
        )


def fetch_configured_sources(config: SourceConfig) -> tuple[SourceFetchResult, ...]:
    """Fetch bounded metadata for all configured sources."""
    return tuple(fetch_source_metadata(source) for source in config.sources)


def load_source_monitor_state(path: Path) -> dict[str, Any]:
    """Load prior source monitor state, returning empty state if missing or invalid."""
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(raw, dict):
        return {}

    return raw


def _previous_sources(state: dict[str, Any]) -> dict[str, Any]:
    sources = state.get("sources", {})
    if not isinstance(sources, dict):
        return {}
    return sources


def _comparison_fields(result: SourceFetchResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "title": result.title,
        "error": result.error,
    }


def classify_source_change(
    result: SourceFetchResult,
    previous: dict[str, Any] | None,
) -> str:
    """Classify current result against prior deterministic metadata."""
    if previous is None:
        return "new"

    current = _comparison_fields(result)
    for key, value in current.items():
        if previous.get(key) != value:
            return "changed"

    return "unchanged"


def apply_change_detection(
    fetch_results: tuple[SourceFetchResult, ...],
    previous_state: dict[str, Any],
) -> tuple[SourceFetchResult, ...]:
    """Annotate fetch results with new, changed, or unchanged."""
    previous = _previous_sources(previous_state)

    annotated: list[SourceFetchResult] = []
    for result in fetch_results:
        previous_entry = previous.get(result.source.name)
        if not isinstance(previous_entry, dict):
            previous_entry = None

        annotated.append(
            replace(
                result,
                change_state=classify_source_change(result, previous_entry),
            )
        )

    return tuple(annotated)


def build_source_monitor_state(
    project_name: str,
    fetch_results: tuple[SourceFetchResult, ...],
    now: datetime,
) -> dict[str, Any]:
    """Build the persisted metadata state for a source monitor project."""
    return {
        "version": 1,
        "project": project_name,
        "updated": now.astimezone(UTC).isoformat(timespec="seconds"),
        "sources": {
            result.source.name: {
                "kind": result.source.kind,
                "url": result.source.url,
                "fetched": result.fetched,
                "status": result.status,
                "title": result.title,
                "error": result.error,
            }
            for result in fetch_results
        },
    }


def write_source_monitor_state(path: Path, state: dict[str, Any]) -> None:
    """Atomically write source monitor metadata state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(path)


def _format_configured_sources(config: SourceConfig) -> list[str]:
    """Format configured source information for the report."""
    lines = [
        "## Configured sources",
        "",
        f"Project: {config.project_name}",
        f"Config path: {config.path}",
        f"Config exists: {str(config.exists).lower()}",
        f"Configured sources: {len(config.sources)}",
        "",
    ]

    if not config.sources:
        lines.extend(
            [
                "No sources are configured.",
                "",
            ]
        )
        return lines

    for source in config.sources:
        state = "enabled" if source.enabled else "disabled"
        lines.extend(
            [
                f"- {source.name}",
                f"  - kind: {source.kind}",
                f"  - state: {state}",
                f"  - url: {source.url}",
            ]
        )

    lines.append("")
    return lines


def _format_fetch_results(fetch_results: tuple[SourceFetchResult, ...]) -> list[str]:
    """Format bounded fetch metadata for the report."""
    lines = [
        "## Fetch results",
        "",
    ]

    if not fetch_results:
        lines.extend(
            [
                "No sources were fetched.",
                "",
            ]
        )
        return lines

    for result in fetch_results:
        source = result.source
        lines.extend(
            [
                f"- {source.name}",
                f"  - kind: {source.kind}",
                f"  - url: {source.url}",
                f"  - fetched: {str(result.fetched).lower()}",
                f"  - status: {result.status if result.status is not None else 'n/a'}",
                f"  - bytes_read: {result.bytes_read}",
                f"  - title: {result.title or 'n/a'}",
                f"  - change: {result.change_state or 'n/a'}",
                f"  - error: {result.error or 'none'}",
            ]
        )

    lines.append("")
    return lines


def build_source_monitor_report(
    now: datetime | None = None,
    config: SourceConfig | None = None,
    fetch_results: tuple[SourceFetchResult, ...] | None = None,
    project_name: str = DEFAULT_SOURCE_PROJECT_NAME,
    state_path: Path | None = None,
) -> str:
    """Build the Markdown body for the source monitor report."""
    if now is None:
        now = datetime.now(UTC)

    if config is None:
        config = load_source_config(project_name=project_name)

    if fetch_results is None:
        fetch_results = fetch_configured_sources(config)

    local_now = now.astimezone()
    report_date = local_now.date().isoformat()
    generated_text = local_now.isoformat(timespec="seconds")

    lines = [
        f"# MarcBot Source Monitor - {config.project_name} - {report_date}",
        "",
        f"Generated: {generated_text}",
        f"MarcBot version: {__version__}",
        f"Project: {config.project_name}",
        "",
        "## Status",
        "",
        "Source monitor bounded fetch metadata, title extraction, "
        "and change detection are installed.",
        "",
        f"Fetch timeout seconds: {FETCH_TIMEOUT_SECONDS}",
        f"Max fetch bytes per source: {MAX_FETCH_BYTES}",
    ]

    if state_path is not None:
        lines.append(f"State path: {state_path}")

    lines.append("")

    lines.extend(_format_configured_sources(config))
    lines.extend(_format_fetch_results(fetch_results))

    lines.extend(
        [
            "## Next steps",
            "",
            "- Add a compact report summary section with counts by change state.",
            "- Keep output local and bounded before adding Telegram delivery.",
            "- Add higher-level summaries only after deterministic fetching is reliable.",
            "",
        ]
    )

    return "\n".join(lines)


def write_source_monitor_report(
    project_name: str = DEFAULT_SOURCE_PROJECT_NAME,
    reports_dir: Path | None = None,
    state_path: Path | None = None,
    now: datetime | None = None,
) -> SourceMonitorResult:
    """Write the source monitor report and update project metadata state."""
    if now is None:
        now = datetime.now(UTC)

    config = load_source_config(project_name=project_name)
    raw_fetch_results = fetch_configured_sources(config)

    target_state_path = (
        state_path if state_path is not None else source_monitor_state_path(config.project_name)
    )
    previous_state = load_source_monitor_state(target_state_path)
    fetch_results = apply_change_detection(raw_fetch_results, previous_state)

    target_reports_dir = (
        reports_dir if reports_dir is not None else source_reports_dir(config.project_name)
    )
    timestamp = now.astimezone().strftime("%Y-%m-%d-%H%M%S")
    target_reports_dir.mkdir(parents=True, exist_ok=True)
    path = target_reports_dir / f"source-monitor-{timestamp}.md"

    body = build_source_monitor_report(
        now=now,
        config=config,
        fetch_results=fetch_results,
        project_name=config.project_name,
        state_path=target_state_path,
    )
    path.write_text(body, encoding="utf-8")

    state = build_source_monitor_state(config.project_name, fetch_results, now)
    write_source_monitor_state(target_state_path, state)

    return SourceMonitorResult(
        path=path,
        message=f"Source monitor report written: {path}",
    )
