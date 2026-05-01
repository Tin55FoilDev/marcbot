"""Local Markdown report generation for MarcBot."""

from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from marcbot import __version__
from marcbot.backup_status import format_backup_status_message
from marcbot.disk import format_disk_report
from marcbot.git_status import format_git_report
from marcbot.paths import WORKSPACE_DIR
from marcbot.service_status import format_service_report

REPORTS_DIR = WORKSPACE_DIR / "reports"


@dataclass(frozen=True)
class ReportResult:
    """Result of generating a local report."""

    path: Path
    message: str


def _safe_section(title: str, body_func) -> str:
    """Return a report section while containing expected local collection failures."""
    try:
        body = body_func()
    except Exception as exc:  # noqa: BLE001 - report generation should remain best-effort.
        body = f"Unable to collect this section: {exc}"

    return f"## {title}\n\n```text\n{body.strip()}\n```\n"


def format_report_runtime_section() -> str:
    """Return CLI-safe runtime details for a local report."""
    lines = [
        f"Host: {platform.node()}",
        f"Platform: {platform.platform()}",
        f"Python: {platform.python_version()}",
    ]

    try:
        uptime_output = subprocess.run(
            ["uptime", "-p"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except OSError as exc:
        lines.append(f"Host uptime: unavailable ({exc})")
    except subprocess.TimeoutExpired:
        lines.append("Host uptime: unavailable (uptime command timed out)")
    else:
        if uptime_output.returncode == 0 and uptime_output.stdout.strip():
            lines.append(f"Host uptime: {uptime_output.stdout.strip()}")
        else:
            lines.append("Host uptime: unavailable")

    return "\n".join(lines)


def build_daily_status_report(now: datetime | None = None) -> str:
    """Build the Markdown body for the daily status report."""
    if now is None:
        now = datetime.now(UTC)

    date_text = now.astimezone().date().isoformat()
    generated_text = now.astimezone().isoformat(timespec="seconds")

    sections = [
        f"# MarcBot Daily Status - {date_text}\n",
        f"Generated: {generated_text}",
        f"Host: {platform.node()}",
        f"MarcBot version: {__version__}",
        "",
        _safe_section("Runtime", format_report_runtime_section),
        _safe_section("Disk", format_disk_report),
        _safe_section("Service", format_service_report),
        _safe_section("Git", format_git_report),
        _safe_section("Backup", format_backup_status_message),
        "## Notes\n",
        "This is a locally generated report scaffold.",
        "",
    ]

    return "\n".join(sections)


def write_daily_status_report(
    reports_dir: Path = REPORTS_DIR,
    now: datetime | None = None,
) -> ReportResult:
    """Write the daily status report to the reports directory."""
    if now is None:
        now = datetime.now(UTC)

    report_date = now.astimezone().date().isoformat()
    reports_dir.mkdir(parents=True, exist_ok=True)

    path = reports_dir / f"daily-status-{report_date}.md"
    body = build_daily_status_report(now=now)
    path.write_text(body, encoding="utf-8")

    return ReportResult(
        path=path,
        message=f"Daily status report written: {path}",
    )
