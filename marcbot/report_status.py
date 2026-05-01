"""Read-only status reporting for MarcBot generated reports."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from marcbot.paths import WORKSPACE_DIR

REPORTS_DIR = WORKSPACE_DIR / "reports"
DAILY_STATUS_GLOB = "daily-status-*.md"
REPORT_TIMER_NAME = "marcbot-daily-status-report.timer"
STALE_REPORT_HOURS = 36


@dataclass(frozen=True)
class ReportStatus:
    """Status of the latest generated report."""

    ok: bool
    message: str


def _format_bytes(size_bytes: int) -> str:
    """Return a compact human-readable byte count."""
    if size_bytes < 1024:
        return f"{size_bytes} B"

    size = float(size_bytes)
    for unit in ("KiB", "MiB", "GiB", "TiB"):
        size /= 1024
        if size < 1024:
            return f"{size:.1f} {unit}"

    return f"{size:.1f} PiB"


def _format_age(seconds: float) -> str:
    """Return a compact human-readable age."""
    if seconds < 0:
        return "in the future"

    minutes = int(seconds // 60)
    if minutes < 1:
        return "less than 1 minute"

    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"

    hours = minutes // 60
    if hours < 48:
        return f"{hours} hour{'s' if hours != 1 else ''}"

    days = hours // 24
    return f"{days} day{'s' if days != 1 else ''}"


def _timer_enabled_state(timer_name: str = REPORT_TIMER_NAME) -> str:
    """Return systemd enablement state for the report timer."""
    try:
        result = subprocess.run(
            ["systemctl", "is-enabled", timer_name],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except OSError as exc:
        return f"unknown ({exc})"
    except subprocess.TimeoutExpired:
        return "unknown (systemctl timed out)"

    state = result.stdout.strip() or result.stderr.strip() or "unknown"
    return state


def _latest_daily_status_report(reports_dir: Path = REPORTS_DIR) -> Path | None:
    """Return the newest daily status report by modification time."""
    try:
        candidates = [path for path in reports_dir.glob(DAILY_STATUS_GLOB) if path.is_file()]
    except OSError:
        return None

    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)


def format_report_status_message(
    reports_dir: Path = REPORTS_DIR,
    now: datetime | None = None,
    timer_state_func=_timer_enabled_state,
) -> str:
    """Format the latest report status for Telegram."""
    if now is None:
        now = datetime.now(UTC)

    lines = ["🤖 MarcBot report status"]

    if not reports_dir.is_dir():
        lines.extend(
            [
                f"Reports directory: {reports_dir}",
                "Latest daily status report: none",
                "Overall: unhealthy - reports directory is missing",
            ],
        )
        return "\n".join(lines)

    latest = _latest_daily_status_report(reports_dir)
    timer_state = timer_state_func()

    if latest is None:
        lines.extend(
            [
                f"Reports directory: {reports_dir}",
                "Latest daily status report: none",
                f"Timer: {REPORT_TIMER_NAME} {timer_state}",
                "Overall: unhealthy - no daily status reports found",
            ],
        )
        return "\n".join(lines)

    try:
        stat = latest.stat()
    except OSError as exc:
        lines.extend(
            [
                f"Latest daily status report: {latest.name}",
                f"Path: {latest}",
                f"Timer: {REPORT_TIMER_NAME} {timer_state}",
                f"Overall: unhealthy - unable to stat report: {exc}",
            ],
        )
        return "\n".join(lines)

    modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
    age_seconds = (now.astimezone(UTC) - modified).total_seconds()
    age_text = _format_age(age_seconds)
    stale = age_seconds > STALE_REPORT_HOURS * 3600

    lines.extend(
        [
            f"Latest daily status report: {latest.name}",
            f"Path: {latest}",
            f"Size: {_format_bytes(stat.st_size)}",
            f"Modified: {modified.astimezone().isoformat(timespec='seconds')}",
            f"Age: {age_text}",
            f"Timer: {REPORT_TIMER_NAME} {timer_state}",
        ],
    )

    if stale:
        lines.append(f"Overall: warning - latest report is older than {STALE_REPORT_HOURS} hours")
    elif timer_state != "enabled":
        lines.append("Overall: warning - report timer is not enabled")
    else:
        lines.append("Overall: healthy")

    return "\n".join(lines)
