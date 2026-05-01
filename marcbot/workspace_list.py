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


@dataclass(frozen=True)
class WorkspaceListResult:
    """Validated workspace listing result."""

    ok: bool
    display_path: str
    entries: tuple[WorkspaceEntry, ...]
    message: str


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


def _usage() -> str:
    """Return operator-facing ls usage."""
    return "Use: /ls [workspace-relative-directory]"


def _reject(message: str) -> WorkspaceListResult:
    """Return a rejected workspace listing result."""
    return WorkspaceListResult(
        ok=False,
        display_path="",
        entries=(),
        message=f"🤖 MarcBot ls\n{message}\n{_usage()}",
    )


def _validate_workspace_directory(
    requested_path: str,
    *,
    workspace_dir: Path = WORKSPACE_DIR,
) -> tuple[Path, str] | WorkspaceListResult:
    """Validate a workspace-relative directory request."""
    clean_request = requested_path.strip()

    try:
        resolved_workspace = workspace_dir.resolve(strict=True)
    except OSError as exc:
        return _reject(f"Workspace directory is unavailable: {exc}")

    if not clean_request:
        return resolved_workspace, "."

    candidate = Path(clean_request)

    if candidate.is_absolute():
        return _reject("Absolute paths are not allowed.")

    if any(part == ".." for part in candidate.parts):
        return _reject("Parent-directory traversal is not allowed.")

    if any(part == "" for part in candidate.parts):
        return _reject("Invalid directory path.")

    try:
        resolved_path = (resolved_workspace / candidate).resolve(strict=True)
    except OSError as exc:
        return _reject(f"Unable to access directory: {exc}")

    if resolved_path != resolved_workspace and resolved_workspace not in resolved_path.parents:
        return _reject("Resolved path is outside the workspace.")

    if not resolved_path.is_dir():
        return _reject("Requested path is not a directory.")

    return resolved_path, clean_request


def list_workspace_directory(directory: Path) -> tuple[WorkspaceEntry, ...]:
    """Return a safe read-only listing of one validated workspace directory."""
    entries: list[WorkspaceEntry] = []

    for child in directory.iterdir():
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


def list_workspace_root(workspace_dir: Path = WORKSPACE_DIR) -> tuple[WorkspaceEntry, ...]:
    """Return a safe read-only listing of the workspace root.

    Kept as a compatibility helper for tests and root-only callers.
    """
    return list_workspace_directory(workspace_dir)


def get_workspace_list_result(
    requested_path: str = "",
    *,
    workspace_dir: Path = WORKSPACE_DIR,
) -> WorkspaceListResult:
    """Validate and list a workspace-relative directory."""
    validated = _validate_workspace_directory(requested_path, workspace_dir=workspace_dir)
    if isinstance(validated, WorkspaceListResult):
        return validated

    directory, display_path = validated

    try:
        entries = list_workspace_directory(directory)
    except OSError as exc:
        return _reject(f"Unable to list workspace directory: {exc}")

    return WorkspaceListResult(
        ok=True,
        display_path=display_path,
        entries=entries,
        message="OK",
    )


def _format_entry(entry: WorkspaceEntry, *, prefix: str) -> str:
    """Format one workspace entry."""
    relative_name = f"{prefix}/{entry.name}" if prefix and prefix != "." else entry.name

    if entry.is_dir:
        return f"📁 {relative_name}/"

    if entry.is_file:
        size = _format_bytes(entry.size_bytes or 0)
        return f"📄 {relative_name} ({size})"

    return f"❓ {relative_name}"


def format_workspace_ls_message(
    entries: tuple[WorkspaceEntry, ...] | None = None,
    *,
    workspace_dir: Path = WORKSPACE_DIR,
    requested_path: str = "",
) -> str:
    """Format a workspace listing for Telegram."""
    if entries is None:
        result = get_workspace_list_result(requested_path, workspace_dir=workspace_dir)
        if not result.ok:
            return result.message
        entries = result.entries
        display_path = result.display_path
    else:
        display_path = requested_path.strip() or "."

    if display_path == ".":
        path_line = "Path: /srv/marcbot/workspace"
    else:
        path_line = f"Path: /srv/marcbot/workspace/{display_path}"

    lines = [
        "🤖 MarcBot workspace",
        path_line,
        "",
    ]

    if not entries:
        lines.append("<empty>")
        lines.append("")
        lines.append("Use /send <workspace-relative-path> to send a file.")
        return "\n".join(lines)

    visible_entries = entries[:MAX_LIST_ENTRIES]
    for entry in visible_entries:
        lines.append(_format_entry(entry, prefix=display_path))

    if len(entries) > MAX_LIST_ENTRIES:
        lines.append(f"... truncated: showing {MAX_LIST_ENTRIES} of {len(entries)} entries")

    lines.append("")
    lines.append("Use /send <workspace-relative-path> to send a file.")

    message = "\n".join(lines)
    if len(message) <= MAX_LIST_MESSAGE_CHARS:
        return message

    return message[:MAX_LIST_MESSAGE_CHARS] + "\n\n[truncated]"
