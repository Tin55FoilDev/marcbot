"""Source monitor report generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from marcbot import __version__
from marcbot.paths import WORKSPACE_DIR
from marcbot.source_config import SourceConfig, SourceDefinition, load_source_config

REPORTS_DIR = WORKSPACE_DIR / "reports"

FETCH_TIMEOUT_SECONDS = 10
MAX_FETCH_BYTES = 256 * 1024
USER_AGENT = f"MarcBot/{__version__} source-monitor"


@dataclass(frozen=True)
class SourceFetchResult:
    """Bounded fetch metadata for one configured source."""

    source: SourceDefinition
    fetched: bool
    status: int | None
    bytes_read: int
    error: str | None = None


@dataclass(frozen=True)
class SourceMonitorResult:
    """Result of writing a source monitor report."""

    path: Path
    message: str


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
            return SourceFetchResult(
                source=source,
                fetched=True,
                status=response.status,
                bytes_read=min(len(data), MAX_FETCH_BYTES),
                error=None,
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


def _format_configured_sources(config: SourceConfig) -> list[str]:
    """Format configured source information for the report."""
    lines = [
        "## Configured sources",
        "",
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
                f"  - error: {result.error or 'none'}",
            ]
        )

    lines.append("")
    return lines


def build_source_monitor_report(
    now: datetime | None = None,
    config: SourceConfig | None = None,
    fetch_results: tuple[SourceFetchResult, ...] | None = None,
) -> str:
    """Build the Markdown body for the source monitor report."""
    if now is None:
        now = datetime.now(UTC)

    if config is None:
        config = load_source_config()

    if fetch_results is None:
        fetch_results = fetch_configured_sources(config)

    local_now = now.astimezone()
    report_date = local_now.date().isoformat()
    generated_text = local_now.isoformat(timespec="seconds")

    lines = [
        f"# MarcBot Source Monitor - {report_date}",
        "",
        f"Generated: {generated_text}",
        f"MarcBot version: {__version__}",
        "",
        "## Status",
        "",
        "Source monitor bounded fetch metadata is installed.",
        "",
        f"Fetch timeout seconds: {FETCH_TIMEOUT_SECONDS}",
        f"Max fetch bytes per source: {MAX_FETCH_BYTES}",
        "",
    ]

    lines.extend(_format_configured_sources(config))
    lines.extend(_format_fetch_results(fetch_results))

    lines.extend(
        [
            "## Next steps",
            "",
            "- Add basic page-title extraction from bounded fetched content.",
            "- Keep output local and bounded before adding Telegram delivery.",
            "- Add higher-level summaries only after deterministic fetching is reliable.",
            "",
        ]
    )

    return "\n".join(lines)


def write_source_monitor_report(
    reports_dir: Path = REPORTS_DIR,
    now: datetime | None = None,
) -> SourceMonitorResult:
    """Write the source monitor report to the reports directory."""
    if now is None:
        now = datetime.now(UTC)

    config = load_source_config()
    fetch_results = fetch_configured_sources(config)

    timestamp = now.astimezone().strftime("%Y-%m-%d-%H%M%S")
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"source-monitor-{timestamp}.md"

    body = build_source_monitor_report(
        now=now,
        config=config,
        fetch_results=fetch_results,
    )
    path.write_text(body, encoding="utf-8")

    return SourceMonitorResult(
        path=path,
        message=f"Source monitor report written: {path}",
    )
