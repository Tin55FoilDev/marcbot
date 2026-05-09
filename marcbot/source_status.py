"""Read-only source monitor status formatting for generic report commands."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from marcbot.errors import MarcBotError
from marcbot.source_config import (
    DEFAULT_SOURCE_PROJECT_NAME,
    load_source_config,
    source_reports_dir,
    source_summaries_dir,
)

SOURCE_REPORT_GLOB = "source-monitor-*.md"
SOURCE_SUMMARY_GLOB = "source-monitor-*.summary.md"
SOURCE_REPORT_NAME_PATTERN = re.compile(r"^source-monitor-(\d{4}-\d{2}-\d{2}-\d{6})\.md$")
SOURCE_SUMMARY_NAME_PATTERN = re.compile(r"^source-monitor-(\d{4}-\d{2}-\d{2}-\d{6})\.summary\.md$")
MAX_SOURCE_STATUS_CHARS = 3500
RECENT_SOURCE_ARTIFACT_LIMIT = 3


SOURCE_ARTIFACT_ID_PATTERN = re.compile(
    r"^(report|summary):(\d{4}-\d{2}-\d{2}-\d{6})$"
)


def resolve_source_monitor_artifact(
    artifact_id: str,
    project_name: str = DEFAULT_SOURCE_PROJECT_NAME,
    reports_dir: Path | None = None,
    summaries_dir: Path | None = None,
) -> Path | None:
    """Resolve a safe source-monitor artifact ID to an approved local path."""
    match = SOURCE_ARTIFACT_ID_PATTERN.match(artifact_id.strip())
    if match is None:
        return None

    artifact_kind, timestamp = match.groups()

    if artifact_kind == "report":
        target_reports_dir = (
            reports_dir if reports_dir is not None else source_reports_dir(project_name)
        )
        candidate = target_reports_dir / f"source-monitor-{timestamp}.md"
    else:
        target_summaries_dir = (
            summaries_dir
            if summaries_dir is not None
            else source_summaries_dir(project_name)
        )
        candidate = target_summaries_dir / f"source-monitor-{timestamp}.summary.md"

    try:
        if not candidate.is_file():
            return None
    except OSError:
        return None

    return candidate


def find_latest_source_monitor_report(
    project_name: str = DEFAULT_SOURCE_PROJECT_NAME,
    reports_dir: Path | None = None,
) -> Path | None:
    """Return the latest local source monitor report path for a project."""
    target_reports_dir = (
        reports_dir if reports_dir is not None else source_reports_dir(project_name)
    )
    reports = sorted(
        path
        for path in target_reports_dir.glob(SOURCE_REPORT_GLOB)
        if source_monitor_artifact_id(path) is not None
        and source_monitor_artifact_id(path).startswith("report:")
    )
    if not reports:
        return None
    return reports[-1]


def find_latest_source_monitor_summary(
    project_name: str = DEFAULT_SOURCE_PROJECT_NAME,
    summaries_dir: Path | None = None,
) -> Path | None:
    """Return the latest local source monitor summary path for a project."""
    target_summaries_dir = (
        summaries_dir
        if summaries_dir is not None
        else source_summaries_dir(project_name)
    )
    summaries = sorted(target_summaries_dir.glob(SOURCE_SUMMARY_GLOB))
    if not summaries:
        return None
    return summaries[-1]


def source_monitor_artifact_id(path: Path) -> str | None:
    """Return a safe source-monitor artifact ID for a report or summary path."""
    summary_match = SOURCE_SUMMARY_NAME_PATTERN.match(path.name)
    if summary_match is not None:
        return f"summary:{summary_match.group(1)}"

    report_match = SOURCE_REPORT_NAME_PATTERN.match(path.name)
    if report_match is not None:
        return f"report:{report_match.group(1)}"

    return None


def find_recent_source_monitor_reports(
    project_name: str = DEFAULT_SOURCE_PROJECT_NAME,
    reports_dir: Path | None = None,
    limit: int = RECENT_SOURCE_ARTIFACT_LIMIT,
) -> list[Path]:
    """Return recent local source monitor report paths for a project."""
    target_reports_dir = (
        reports_dir if reports_dir is not None else source_reports_dir(project_name)
    )
    reports = sorted(
        (
            path
            for path in target_reports_dir.glob(SOURCE_REPORT_GLOB)
            if source_monitor_artifact_id(path) is not None
            and source_monitor_artifact_id(path).startswith("report:")
        ),
        reverse=True,
    )
    return reports[:limit]


def find_recent_source_monitor_summaries(
    project_name: str = DEFAULT_SOURCE_PROJECT_NAME,
    summaries_dir: Path | None = None,
    limit: int = RECENT_SOURCE_ARTIFACT_LIMIT,
) -> list[Path]:
    """Return recent local source monitor summary paths for a project."""
    target_summaries_dir = (
        summaries_dir
        if summaries_dir is not None
        else source_summaries_dir(project_name)
    )
    summaries = sorted(target_summaries_dir.glob(SOURCE_SUMMARY_GLOB), reverse=True)
    return summaries[:limit]


def _format_recent_artifact_lines(label: str, paths: list[Path]) -> list[str]:
    lines = [f"{label}:"]
    if not paths:
        lines.append("- none found")
        return lines

    for path in paths:
        artifact_id = source_monitor_artifact_id(path)
        if artifact_id is None:
            lines.append(f"- {path.name}")
        else:
            lines.append(f"- {artifact_id} — {path.name}")

    return lines


def _format_recent_artifact_id_lines(paths: list[Path]) -> list[str]:
    lines: list[str] = []
    for path in paths:
        artifact_id = source_monitor_artifact_id(path)
        if artifact_id is not None:
            lines.append(f"- {artifact_id}")

    if not lines:
        return ["- none found"]

    return lines


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


def _file_modified_datetime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)


def _format_file_timestamp(path: Path) -> str:
    return _file_modified_datetime(path).isoformat(timespec="seconds")


def _format_elapsed_since(timestamp: datetime, now: datetime) -> str:
    elapsed_seconds = max(0, int((now - timestamp).total_seconds()))

    if elapsed_seconds < 60:
        return "less than 1 minute ago"

    elapsed_minutes = elapsed_seconds // 60
    if elapsed_minutes < 60:
        unit = "minute" if elapsed_minutes == 1 else "minutes"
        return f"{elapsed_minutes} {unit} ago"

    elapsed_hours = elapsed_minutes // 60
    if elapsed_hours < 48:
        unit = "hour" if elapsed_hours == 1 else "hours"
        return f"{elapsed_hours} {unit} ago"

    elapsed_days = elapsed_hours // 24
    unit = "day" if elapsed_days == 1 else "days"
    return f"{elapsed_days} {unit} ago"


def _has_meaningful_value(value: str | None) -> bool:
    return value not in {None, "", "n/a", "none", "None"}


def _summarize_report_state(report_text: str) -> str:
    blocks = _parse_fetch_result_blocks(report_text)
    if not blocks:
        return "Report state: no fetch-result entries found"

    changed_sources: list[str] = []
    error_sources: list[str] = []

    for block in blocks:
        name = block.get("name", "unknown-source")
        change = block.get("change", "")
        status = block.get("status", "")
        error = block.get("error")

        if change not in {"", "n/a", "unchanged"}:
            changed_sources.append(name)

        if status == "error" or _has_meaningful_value(error):
            error_sources.append(name)

    parts: list[str] = []
    if changed_sources:
        parts.append(f"changed sources: {len(changed_sources)}")
    if error_sources:
        parts.append(f"errors: {len(error_sources)}")
    if not parts:
        parts.append("no changes or errors detected")

    return "Report state: " + "; ".join(parts)


def format_source_monitor_cli_status(
    project_name: str = DEFAULT_SOURCE_PROJECT_NAME,
    reports_dir: Path | None = None,
    summaries_dir: Path | None = None,
) -> str:
    """Format a read-only CLI status for saved source monitor artifacts."""
    try:
        config = load_source_config(project_name=project_name)
        target_reports_dir = (
            reports_dir if reports_dir is not None else source_reports_dir(project_name)
        )
        target_summaries_dir = (
            summaries_dir
            if summaries_dir is not None
            else source_summaries_dir(project_name)
        )
    except MarcBotError as exc:
        return (
            "MarcBot source monitor status\n"
            f"Project: {project_name}\n"
            "Config: invalid\n"
            f"Error: {exc.code}: {exc.message}"
        )

    latest_report = find_latest_source_monitor_report(
        project_name=project_name,
        reports_dir=target_reports_dir,
    )
    latest_summary = find_latest_source_monitor_summary(
        project_name=project_name,
        summaries_dir=target_summaries_dir,
    )
    recent_reports = find_recent_source_monitor_reports(
        project_name=project_name,
        reports_dir=target_reports_dir,
    )
    recent_summaries = find_recent_source_monitor_summaries(
        project_name=project_name,
        summaries_dir=target_summaries_dir,
    )
    now = datetime.now(tz=UTC)
    report_modified: datetime | None = None
    summary_modified: datetime | None = None

    lines = [
        "MarcBot source monitor status",
        f"Project: {config.project_name}",
        "Config: valid",
        f"Config path: {config.path}",
        f"Reports dir: {target_reports_dir}",
        f"Summaries dir: {target_summaries_dir}",
        "",
        *_format_recent_artifact_lines("Recent reports", recent_reports),
        "",
        *_format_recent_artifact_lines("Recent summaries", recent_summaries),
    ]

    if latest_report is None:
        lines.extend(
            [
                "Latest report: none found",
                f"Run: python -m marcbot source-monitor run {project_name}",
            ]
        )
    else:
        lines.append(f"Latest report: {latest_report}")
        try:
            report_modified = _file_modified_datetime(latest_report)
            lines.append(f"Report modified: {report_modified.isoformat(timespec='seconds')}")
            lines.append(f"Report age: {_format_elapsed_since(report_modified, now)}")
            report_text = latest_report.read_text(encoding="utf-8")
        except OSError as exc:
            lines.append(
                "Report read status: error: "
                f"{exc.strerror or exc.__class__.__name__}"
            )
        else:
            generated_line = _extract_generated_line(report_text)
            if generated_line is not None:
                lines.append(generated_line)
            lines.append(_summarize_report_state(report_text))

    if latest_summary is None:
        lines.append("Latest summary: none found")
    else:
        lines.append(f"Latest summary: {latest_summary}")
        try:
            summary_modified = _file_modified_datetime(latest_summary)
            lines.append(f"Summary modified: {summary_modified.isoformat(timespec='seconds')}")
            lines.append(f"Summary age: {_format_elapsed_since(summary_modified, now)}")
        except OSError as exc:
            lines.append(
                "Summary read status: error: "
                f"{exc.strerror or exc.__class__.__name__}"
            )

    if report_modified is not None and summary_modified is not None:
        if summary_modified < report_modified:
            lines.append("Summary freshness: older than latest report")
        else:
            lines.append("Summary freshness: current with latest report")

    return "\n".join(lines)


def format_source_status_message(
    project_name: str = DEFAULT_SOURCE_PROJECT_NAME,
    reports_dir: Path | None = None,
    summaries_dir: Path | None = None,
) -> str:
    """Format latest local source monitor summary for Telegram."""
    try:
        target_reports_dir = (
            reports_dir if reports_dir is not None else source_reports_dir(project_name)
        )
        target_summaries_dir = (
            summaries_dir
            if summaries_dir is not None
            else source_summaries_dir(project_name)
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
    recent_reports = find_recent_source_monitor_reports(
        project_name=project_name,
        reports_dir=target_reports_dir,
    )
    recent_summaries = find_recent_source_monitor_summaries(
        project_name=project_name,
        summaries_dir=target_summaries_dir,
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
            "",
            "Recent artifacts:",
            *_format_recent_artifact_id_lines(recent_reports + recent_summaries),
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
