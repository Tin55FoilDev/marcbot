"""Read-only MarcBot backup status helpers."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from marcbot.paths import BACKUP_DIR

LATEST_BACKUP_FILE = BACKUP_DIR / "latest-backup.txt"
MAX_BACKUP_AGE_SECONDS = 36 * 60 * 60


@dataclass(frozen=True)
class BackupMarker:
    """Parsed latest-backup.txt metadata."""

    name: str
    path: Path
    sha256_path: Path
    created_iso: str
    created_epoch: int
    size_bytes: int
    retention_days: int


@dataclass(frozen=True)
class BackupStatus:
    """Read-only backup status report."""

    ok: bool
    marker: BackupMarker | None
    messages: tuple[str, ...]


def _format_bytes(byte_count: int) -> str:
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


def _format_age(seconds: int) -> str:
    """Format age seconds for operator output."""
    seconds = max(0, seconds)
    days, remainder = divmod(seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, _ = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours or days:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if not days:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    return ", ".join(parts)


def _parse_marker_line(line: str) -> tuple[str, str] | None:
    """Parse one key=value marker line."""
    if not line.strip() or line.lstrip().startswith("#"):
        return None

    if "=" not in line:
        return None

    key, value = line.split("=", 1)
    return key.strip(), value.strip()


def parse_backup_marker(marker_file: Path = LATEST_BACKUP_FILE) -> BackupMarker:
    """Parse latest-backup.txt into a BackupMarker."""
    data: dict[str, str] = {}

    for line in marker_file.read_text(encoding="utf-8", errors="replace").splitlines():
        parsed = _parse_marker_line(line)
        if parsed is None:
            continue
        key, value = parsed
        data[key] = value

    required = (
        "name",
        "path",
        "sha256_path",
        "created_iso",
        "created_epoch",
        "size_bytes",
        "retention_days",
    )
    missing = [key for key in required if key not in data]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"missing marker fields: {missing_text}")

    return BackupMarker(
        name=data["name"],
        path=Path(data["path"]),
        sha256_path=Path(data["sha256_path"]),
        created_iso=data["created_iso"],
        created_epoch=int(data["created_epoch"]),
        size_bytes=int(data["size_bytes"]),
        retention_days=int(data["retention_days"]),
    )


def get_backup_status(
    marker_file: Path = LATEST_BACKUP_FILE,
    *,
    now_epoch: int | None = None,
    max_age_seconds: int = MAX_BACKUP_AGE_SECONDS,
) -> BackupStatus:
    """Return read-only backup status from the latest backup marker."""
    messages: list[str] = []

    if now_epoch is None:
        now_epoch = int(time.time())

    if not marker_file.is_file():
        return BackupStatus(
            ok=False,
            marker=None,
            messages=(f"ERROR: latest marker missing: {marker_file}",),
        )

    try:
        marker = parse_backup_marker(marker_file)
    except (OSError, ValueError) as exc:
        return BackupStatus(
            ok=False,
            marker=None,
            messages=(f"ERROR: unable to parse latest marker: {exc}",),
        )

    archive_ok = True
    sha_ok = True
    age_ok = True

    if not marker.path.is_file():
        archive_ok = False
        messages.append(f"ERROR: archive missing: {marker.path}")
    else:
        actual_size = marker.path.stat().st_size
        if actual_size <= 0:
            archive_ok = False
            messages.append("ERROR: archive is zero bytes")
        elif actual_size != marker.size_bytes:
            messages.append(
                f"WARN: archive size changed: marker={marker.size_bytes} actual={actual_size}",
            )
        else:
            messages.append("OK: archive present")

    if not marker.sha256_path.is_file():
        sha_ok = False
        messages.append(f"ERROR: checksum missing: {marker.sha256_path}")
    else:
        messages.append("OK: checksum present")

    age_seconds = max(0, now_epoch - marker.created_epoch)
    if age_seconds > max_age_seconds:
        age_ok = False
        messages.append(
            f"WARN: latest backup is old: {_format_age(age_seconds)} "
            f"threshold={_format_age(max_age_seconds)}",
        )
    else:
        messages.append(f"OK: latest backup age {_format_age(age_seconds)}")

    return BackupStatus(
        ok=archive_ok and sha_ok and age_ok,
        marker=marker,
        messages=tuple(messages),
    )


def format_backup_status_message(status: BackupStatus | None = None) -> str:
    """Format a Telegram-friendly backup status report."""
    if status is None:
        status = get_backup_status()

    lines = ["🤖 MarcBot backup status"]

    if status.marker is None:
        lines.extend(status.messages)
        lines.append("Overall: unhealthy")
        return "\n".join(lines)

    marker = status.marker
    lines.extend(
        [
            f"Latest backup: {marker.name}",
            f"Created: {marker.created_iso}",
            f"Size: {_format_bytes(marker.size_bytes)}",
            f"Retention: {marker.retention_days} days",
            f"Archive: {marker.path}",
            f"SHA256: {marker.sha256_path}",
            "",
        ],
    )
    lines.extend(status.messages)
    lines.append(f"Overall: {'healthy' if status.ok else 'unhealthy'}")

    return "\n".join(lines)
