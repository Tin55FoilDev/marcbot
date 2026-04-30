"""Uptime helpers for MarcBot."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

PROC_UPTIME = Path("/proc/uptime")


def format_duration(total_seconds: float) -> str:
    """Format a duration in seconds as a compact human-readable string."""
    seconds = max(0, int(total_seconds))

    days, remainder = divmod(seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, seconds = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours or days:
        parts.append(f"{hours:02d} hour{'s' if hours != 1 else ''}")
    if minutes or hours or days:
        parts.append(f"{minutes:02d} minute{'s' if minutes != 1 else ''}")
    parts.append(f"{seconds:02d} second{'s' if seconds != 1 else ''}")

    return ", ".join(parts)


def read_host_uptime_seconds(path: Path = PROC_UPTIME) -> float:
    """Read host uptime seconds from /proc/uptime."""
    text = path.read_text(encoding="utf-8").strip()
    first_value = text.split()[0]
    return float(first_value)


def process_uptime_seconds(started_at: datetime, now: datetime | None = None) -> float:
    """Return process uptime seconds from a startup timestamp."""
    current_time = now or datetime.now(UTC)

    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)

    return max(0.0, (current_time - started_at).total_seconds())


def format_uptime_report(
    *,
    process_started_at: datetime,
    host_uptime_seconds: float | None = None,
    now: datetime | None = None,
) -> str:
    """Format a Telegram-friendly MarcBot uptime report."""
    if host_uptime_seconds is None:
        host_uptime_seconds = read_host_uptime_seconds()

    proc_seconds = process_uptime_seconds(process_started_at, now=now)

    return (
        "🤖 MarcBot uptime\n"
        f"Host uptime: {format_duration(host_uptime_seconds)}\n"
        f"Process uptime: {format_duration(proc_seconds)}"
    )
