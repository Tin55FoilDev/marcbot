"""Safe workspace file validation for Telegram file sending."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marcbot.paths import WORKSPACE_DIR

MAX_SEND_BYTES = 10_000_000


@dataclass(frozen=True)
class WorkspaceSendResult:
    """Result of validating a workspace-relative file send request."""

    ok: bool
    path: Path | None
    message: str


def _available_usage() -> str:
    """Return the operator-facing /send usage line."""
    return "Use: /send <workspace-relative-path>"


def _reject(message: str) -> WorkspaceSendResult:
    """Return a rejected workspace send result."""
    return WorkspaceSendResult(
        ok=False,
        path=None,
        message=f"🤖 MarcBot send\n{message}\n{_available_usage()}",
    )


def validate_workspace_send(requested_path: str) -> WorkspaceSendResult:
    """Validate a workspace-relative path for Telegram file sending.

    Security model:
    - paths are relative to /srv/marcbot/workspace
    - absolute paths are rejected
    - parent traversal is rejected
    - resolved path must remain under /srv/marcbot/workspace
    - path must be a regular file
    - file size must be under MAX_SEND_BYTES
    """

    clean_request = requested_path.strip()
    if not clean_request:
        return _reject("Missing file path.")

    candidate = Path(clean_request)

    if candidate.is_absolute():
        return _reject("Absolute paths are not allowed.")

    if any(part == ".." for part in candidate.parts):
        return _reject("Parent-directory traversal is not allowed.")

    if any(part == "" for part in candidate.parts):
        return _reject("Invalid file path.")

    try:
        resolved_workspace = WORKSPACE_DIR.resolve(strict=True)
    except OSError as exc:
        return _reject(f"Workspace directory is unavailable: {exc}")

    try:
        resolved_path = (resolved_workspace / candidate).resolve(strict=True)
    except OSError as exc:
        return _reject(f"Unable to access file: {exc}")

    if resolved_path != resolved_workspace and resolved_workspace not in resolved_path.parents:
        return _reject("Resolved path is outside the workspace.")

    if not resolved_path.is_file():
        return _reject("Requested path is not a regular file.")

    try:
        size_bytes = resolved_path.stat().st_size
    except OSError as exc:
        return _reject(f"Unable to inspect file: {exc}")

    if size_bytes > MAX_SEND_BYTES:
        return _reject(
            f"File is too large to send: {size_bytes} bytes limit={MAX_SEND_BYTES} bytes.",
        )

    return WorkspaceSendResult(
        ok=True,
        path=resolved_path,
        message=f"Sending workspace file: {clean_request}",
    )
