"""Read-only listing of recent MarcBot app-level backups."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from marcbot.paths import BACKUP_DIR

BACKUP_GLOB = "marcbot-backup-*.tar.gz"
DEFAULT_BACKUP_LIMIT = 5


@dataclass(frozen=True)
class BackupEntry:
    """Metadata for one MarcBot backup archive."""

    path: Path
    size_bytes: int
    modified: datetime
    sha256_present: bool


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


def list_recent_backups(
    backup_dir: Path = BACKUP_DIR,
    limit: int = DEFAULT_BACKUP_LIMIT,
) -> list[BackupEntry]:
    """Return recent backup archives, newest first."""
    if limit < 1:
        return []

    try:
        candidates = [path for path in backup_dir.glob(BACKUP_GLOB) if path.is_file()]
    except OSError:
        return []

    entries: list[BackupEntry] = []

    for path in candidates:
        try:
            stat = path.stat()
        except OSError:
            continue

        entries.append(
            BackupEntry(
                path=path,
                size_bytes=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                sha256_present=Path(f"{path}.sha256").is_file(),
            ),
        )

    entries.sort(key=lambda entry: entry.modified, reverse=True)
    return entries[:limit]


def format_backup_list_message(
    backup_dir: Path = BACKUP_DIR,
    now: datetime | None = None,
    limit: int = DEFAULT_BACKUP_LIMIT,
) -> str:
    """Format recent backup archives for Telegram."""
    if now is None:
        now = datetime.now(UTC)

    lines = ["🤖 MarcBot backup list"]

    if not backup_dir.is_dir():
        lines.extend(
            [
                f"Backup directory: {backup_dir}",
                "Recent app-level backups: none",
                "Overall: unhealthy - backup directory is missing",
            ],
        )
        return "\n".join(lines)

    backups = list_recent_backups(backup_dir=backup_dir, limit=limit)

    if not backups:
        lines.extend(
            [
                f"Backup directory: {backup_dir}",
                "Recent app-level backups: none",
                "Overall: warning - no backup archives found",
            ],
        )
        return "\n".join(lines)

    lines.append(f"Backup directory: {backup_dir}")
    lines.append("")
    lines.append("Recent app-level backups:")

    for index, entry in enumerate(backups, start=1):
        age_seconds = (now.astimezone(UTC) - entry.modified).total_seconds()
        sha_text = "present" if entry.sha256_present else "missing"

        lines.extend(
            [
                "",
                f"{index}. {entry.path.name}",
                f"   Size: {_format_bytes(entry.size_bytes)}",
                f"   Modified: {entry.modified.astimezone().isoformat(timespec='seconds')}",
                f"   Age: {_format_age(age_seconds)}",
                f"   SHA256: {sha_text}",
            ],
        )

    if any(not entry.sha256_present for entry in backups):
        lines.append("")
        lines.append("Overall: warning - one or more checksum files are missing")
    else:
        lines.append("")
        lines.append("Overall: healthy")

    return "\n".join(lines)
