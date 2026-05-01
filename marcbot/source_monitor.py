"""Source monitor report generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from marcbot import __version__
from marcbot.paths import WORKSPACE_DIR
from marcbot.source_config import SourceConfig, load_source_config

REPORTS_DIR = WORKSPACE_DIR / "reports"


@dataclass(frozen=True)
class SourceMonitorResult:
    """Result of writing a source monitor report."""

    path: Path
    message: str


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


def build_source_monitor_report(
    now: datetime | None = None,
    config: SourceConfig | None = None,
) -> str:
    """Build the Markdown body for the source monitor report."""
    if now is None:
        now = datetime.now(UTC)

    if config is None:
        config = load_source_config()

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
        "Source monitor config integration is installed.",
        "",
        "No sources were fetched in this version.",
        "",
    ]

    lines.extend(_format_configured_sources(config))

    lines.extend(
        [
            "## Next steps",
            "",
            "- Add bounded fetch behavior for enabled allowlisted sources.",
            "- Capture HTTP status, content size, and basic page title when available.",
            "- Keep output local and bounded before adding Telegram delivery.",
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

    timestamp = now.astimezone().strftime("%Y-%m-%d-%H%M%S")
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"source-monitor-{timestamp}.md"

    body = build_source_monitor_report(now=now, config=load_source_config())
    path.write_text(body, encoding="utf-8")

    return SourceMonitorResult(
        path=path,
        message=f"Source monitor report written: {path}",
    )
