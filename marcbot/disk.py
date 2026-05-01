"""Disk usage helpers for MarcBot."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from marcbot.paths import PROJECT_ROOT


@dataclass(frozen=True)
class DiskUsage:
    """Disk usage summary for one filesystem path."""

    path: Path
    total_bytes: int
    used_bytes: int
    free_bytes: int

    @property
    def percent_used(self) -> float:
        """Return percentage of disk used."""
        if self.total_bytes <= 0:
            return 0.0
        return (self.used_bytes / self.total_bytes) * 100


def format_bytes(byte_count: int) -> str:
    """Format bytes as a compact binary-size string."""
    value = float(byte_count)
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")

    for unit in units:
        if abs(value) < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0

    return f"{value:.1f} PiB"


def get_disk_usage(path: Path) -> DiskUsage:
    """Return disk usage for a path."""
    usage = shutil.disk_usage(path)

    return DiskUsage(
        path=path,
        total_bytes=usage.total,
        used_bytes=usage.used,
        free_bytes=usage.free,
    )


def format_disk_usage_line(label: str, usage: DiskUsage) -> str:
    """Format one disk usage line for operator output."""
    return (
        f"{label}: {format_bytes(usage.used_bytes)} used / "
        f"{format_bytes(usage.total_bytes)} total "
        f"({usage.percent_used:.1f}% used, {format_bytes(usage.free_bytes)} free)"
    )


def format_disk_report(project_root: Path = PROJECT_ROOT) -> str:
    """Format a Telegram-friendly disk usage report."""
    root_usage = get_disk_usage(Path("/"))
    project_usage = get_disk_usage(project_root)

    return (
        "🤖 MarcBot disk\n"
        f"{format_disk_usage_line('Root filesystem', root_usage)}\n"
        f"{format_disk_usage_line('/srv/marcbot', project_usage)}"
    )
