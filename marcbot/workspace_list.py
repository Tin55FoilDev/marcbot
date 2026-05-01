"""Safe read-only workspace listing helpers for MarcBot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marcbot.paths import WORKSPACE_DIR

MAX_LIST_ENTRIES = 50
MAX_LIST_MESSAGE_CHARS = 3500


@dataclass(frozen=True)
class WorkspaceEntry:
    """One visible workspace entry."""

    name: str
    path: Path
    is_dir: bool
    is_file: bool
    size_bytes: int | None


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


def _entry_sort_key(entry: WorkspaceEntry) -> tuple[int, str]:
    """Sort directories first, then files, both alphabetically."""
    return (0 if entry.is_dir else 1, entry.name.lower())


def list_workspace_root(workspace_dir: Path = WORKSPACE_DIR) -> tuple[WorkspaceEntry, ...]:
    """Return a safe read-only listing of the workspace root."""
    if not workspace_dir.is_dir():
        raise FileNotFoundError(f"workspace directory not found: {workspace_dir}")

    entries: list[WorkspaceEntry] = []

    for child in workspace_dir.iterdir():
        name = child.name

        # Keep hidden/internal files out of the Telegram listing.
        if name.startswith("."):
            continue

        try:
            is_dir = child.is_dir()
            is_file = child.is_file()
            size_bytes = child.stat().st_size if is_file else None
        except OSError:
            continue

        entries.append(
            WorkspaceEntry(
                name=name,
                path=child,
                is_dir=is_dir,
                is_file=is_file,
                size_bytes=size_bytes,
            ),
        )

    return tuple(sorted(entries, key=_entry_sort_key))


def _format_entry(entry: WorkspaceEntry) -> str:
    """Format one workspace entry."""
    if entry.is_dir:
        return f"📁 {entry.name}/"

    if entry.is_file:
        size = _format_bytes(entry.size_bytes or 0)
        return f"📄 {entry.name} ({size})"

    return f"❓ {entry.name}"


def format_workspace_ls_message(
    entries: tuple[WorkspaceEntry, ...] | None = None,
    *,
    workspace_dir: Path = WORKSPACE_DIR,
) -> str:
    """Format the workspace root listing for Telegram."""
    if entries is None:
        try:
            entries = list_workspace_root(workspace_dir)
        except FileNotFoundError as exc:
            return f"🤖 MarcBot ls\nERROR: {exc}"
        except OSError as exc:
            return f"🤖 MarcBot ls\nERROR: unable to list workspace: {exc}"

    lines = [
        "🤖 MarcBot workspace",
        f"Path: {workspace_dir}",
        "",
    ]

    if not entries:
        lines.append("<empty>")
        lines.append("")
        lines.append("Use /send <workspace-relative-path> to send a file.")
        return "\n".join(lines)

    visible_entries = entries[:MAX_LIST_ENTRIES]
    for entry in visible_entries:
        lines.append(_format_entry(entry))

    if len(entries) > MAX_LIST_ENTRIES:
        lines.append(f"... truncated: showing {MAX_LIST_ENTRIES} of {len(entries)} entries")

    lines.append("")
    lines.append("Use /send <workspace-relative-path> to send a file.")

    message = "\n".join(lines)
    if len(message) <= MAX_LIST_MESSAGE_CHARS:
        return message

    return message[:MAX_LIST_MESSAGE_CHARS] + "\n\n[truncated]"
