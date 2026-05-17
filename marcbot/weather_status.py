"""Weather report status formatting for MarcBot."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from marcbot.weather_report import WEATHER_REPORTS_DIR, find_latest_weather_report


def _format_modified_time(path: Path) -> str:
    """Return an ISO timestamp for a file modification time."""

    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return modified.isoformat()


def format_weather_status_message(
    reports_dir: Path = WEATHER_REPORTS_DIR,
) -> str:
    """Format provider-free weather report status."""

    lines = [
        "MarcBot weather report",
        f"Reports dir: {reports_dir}",
    ]

    if not reports_dir.is_dir():
        lines.extend(
            [
                "Latest report: missing",
                "Status: reports directory not found",
                "Timer: see /timer_status",
                "Provider contact: no",
            ]
        )
        return "\n".join(lines)

    latest = find_latest_weather_report(reports_dir=reports_dir)
    if latest is None:
        lines.extend(
            [
                "Latest report: none",
                "Status: no weather reports found",
                "Timer: see /timer_status",
                "Provider contact: no",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            f"Latest report: {latest.name}",
            f"Latest modified: {_format_modified_time(latest)}",
            "Status: latest weather report found",
            "Timer: see /timer_status",
            "Provider contact: no",
        ]
    )
    return "\n".join(lines)
