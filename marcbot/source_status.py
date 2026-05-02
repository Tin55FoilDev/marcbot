"""Read-only source monitor status formatting for generic report commands."""

from __future__ import annotations

from pathlib import Path

from marcbot.errors import MarcBotError
from marcbot.source_config import DEFAULT_SOURCE_PROJECT_NAME, source_reports_dir

SOURCE_REPORT_GLOB = "source-monitor-*.md"
MAX_SOURCE_STATUS_CHARS = 3500


def find_latest_source_monitor_report(
    project_name: str = DEFAULT_SOURCE_PROJECT_NAME,
    reports_dir: Path | None = None,
) -> Path | None:
    """Return the latest local source monitor report path for a project."""
    target_reports_dir = (
        reports_dir if reports_dir is not None else source_reports_dir(project_name)
    )
    reports = sorted(target_reports_dir.glob(SOURCE_REPORT_GLOB))
    if not reports:
        return None
    return reports[-1]


def extract_source_report_summary(report_text: str) -> str | None:
    """Extract the bounded Summary and Observations sections from a report."""
    lines = report_text.splitlines()
    start_index: int | None = None

    for index, line in enumerate(lines):
        if line.strip() == "## Summary":
            start_index = index
            break

    if start_index is None:
        return None

    end_index = len(lines)
    for index in range(start_index + 1, len(lines)):
        line = lines[index].strip()
        if line.startswith("## ") and line not in {"## Summary", "## Observations"}:
            end_index = index
            break

    summary = "\n".join(lines[start_index:end_index]).strip()
    return summary or None


def _parse_fetch_result_blocks(report_text: str) -> list[dict[str, str]]:
    """Parse source blocks from the Fetch results section."""
    lines = report_text.splitlines()
    in_fetch_results = False
    blocks: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for line in lines:
        stripped = line.strip()

        if stripped == "## Fetch results":
            in_fetch_results = True
            continue

        if not in_fetch_results:
            continue

        if stripped.startswith("## "):
            break

        if line.startswith("- "):
            if current is not None:
                blocks.append(current)
            current = {"name": line[2:].strip()}
            continue

        if current is not None and line.startswith("  - ") and ": " in line:
            key, value = line[4:].split(": ", 1)
            current[key.strip()] = value.strip()

    if current is not None:
        blocks.append(current)

    return blocks


def extract_source_report_rss_highlights(report_text: str) -> str | None:
    """Extract compact RSS latest-item highlights from a source monitor report."""
    highlights: list[str] = []

    for block in _parse_fetch_result_blocks(report_text):
        if block.get("kind") != "rss_feed":
            continue

        latest_title = block.get("latest_item_title", "n/a")
        if latest_title == "n/a":
            continue

        name = block.get("name", "unknown-source")
        latest_published = block.get("latest_item_published", "n/a")
        highlights.append(f"- {name}: {latest_title}")
        if latest_published != "n/a":
            highlights.append(f"  published: {latest_published}")

    if not highlights:
        return None

    return "\n".join(["## RSS latest items", "", *highlights])



def _extract_generated_line(report_text: str) -> str | None:
    for line in report_text.splitlines():
        if line.startswith("Generated: "):
            return line
    return None


def format_source_status_message(
    project_name: str = DEFAULT_SOURCE_PROJECT_NAME,
    reports_dir: Path | None = None,
) -> str:
    """Format latest local source monitor summary for Telegram."""
    try:
        target_reports_dir = (
            reports_dir if reports_dir is not None else source_reports_dir(project_name)
        )
    except MarcBotError as exc:
        return (
            "🤖 MarcBot source monitor report status\n"
            f"Project: {project_name}\n"
            "Status: invalid project name\n"
            f"Error: {exc.code}: {exc.message}"
        )

    latest_report = find_latest_source_monitor_report(
        project_name=project_name,
        reports_dir=target_reports_dir,
    )

    if latest_report is None:
        return (
            "🤖 MarcBot source monitor report status\n"
            f"Project: {project_name}\n"
            "Status: no local report found\n"
            f"Expected reports dir: {target_reports_dir}\n"
            "Run: python -m marcbot source-monitor run "
            f"{project_name}"
        )

    try:
        report_text = latest_report.read_text(encoding="utf-8")
    except OSError as exc:
        return (
            "🤖 MarcBot source monitor report status\n"
            f"Project: {project_name}\n"
            "Status: could not read latest report\n"
            f"Report: {latest_report}\n"
            f"Error: {exc.strerror or exc.__class__.__name__}"
        )

    summary = extract_source_report_summary(report_text)
    generated_line = _extract_generated_line(report_text)

    if summary is None:
        message = (
            "🤖 MarcBot source monitor report status\n"
            f"Project: {project_name}\n"
            "Status: latest report has no summary section\n"
            f"Report: {latest_report}"
        )
    else:
        message_parts = [
            "🤖 MarcBot source monitor report status",
            f"Project: {project_name}",
            f"Report: {latest_report}",
        ]
        if generated_line is not None:
            message_parts.append(generated_line)
        message_parts.extend(["", summary])

        rss_highlights = extract_source_report_rss_highlights(report_text)
        if rss_highlights is not None:
            message_parts.extend(["", rss_highlights])

        message = "\n".join(message_parts)

    if len(message) <= MAX_SOURCE_STATUS_CHARS:
        return message

    return message[: MAX_SOURCE_STATUS_CHARS - 80].rstrip() + "\n\n[truncated]"
