"""Allowlisted source monitoring report generation for MarcBot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from marcbot import __version__
from marcbot.paths import WORKSPACE_DIR

REPORTS_DIR = WORKSPACE_DIR / "reports"


@dataclass(frozen=True)
class SourceMonitorResult:
    """Result of generating a source monitor report."""

    path: Path
    message: str


def build_source_monitor_report(now: datetime | None = None) -> str:
    """Build the Markdown body for the source monitor report scaffold."""
    if now is None:
        now = datetime.now(UTC)

    report_date = now.astimezone().date().isoformat()
    generated_text = now.astimezone().isoformat(timespec="seconds")

    sections = [
        f"# MarcBot Source Monitor - {report_date}",
        "",
        f"Generated: {generated_text}",
        f"MarcBot version: {__version__}",
        "",
        "## Status",
        "",
        "Source monitor scaffold is installed.",
        "",
        "No sources were checked in this scaffold version.",
        "",
        "## Next steps",
        "",
        "- Add an allowlisted local source configuration file.",
        "- Validate source definitions before any network access.",
        "- Fetch only approved source URLs.",
        "- Write summarized source check results into this report.",
        "",
    ]

    return "\n".join(sections)


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
    body = build_source_monitor_report(now=now)
    path.write_text(body, encoding="utf-8")

    return SourceMonitorResult(
        path=path,
        message=f"Source monitor report written: {path}",
    )
