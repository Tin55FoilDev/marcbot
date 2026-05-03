"""Workspace-bounded file summarization helpers for MarcBot LLM workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marcbot.errors import MarcBotError
from marcbot.paths import WORKSPACE_DIR

MAX_SUMMARY_FILE_CHARS = 3000


@dataclass(frozen=True)
class WorkspaceSummaryInput:
    """Validated workspace file content prepared for summarization."""

    requested_path: str
    resolved_path: Path
    text: str


def _clean_workspace_relative_path(requested_path: str) -> Path:
    if not isinstance(requested_path, str) or not requested_path.strip():
        raise MarcBotError(
            "MBOT-LLM-048",
            "Workspace summary file path must not be empty",
        )

    candidate = Path(requested_path.strip())

    if candidate.is_absolute():
        raise MarcBotError(
            "MBOT-LLM-049",
            "Workspace summary file path must be workspace-relative",
        )

    if any(part == ".." for part in candidate.parts):
        raise MarcBotError(
            "MBOT-LLM-050",
            "Workspace summary file path must not contain parent traversal",
        )

    return candidate


def load_workspace_summary_input(
    requested_path: str,
    workspace_dir: Path = WORKSPACE_DIR,
) -> WorkspaceSummaryInput:
    """Load bounded text from a workspace-relative file."""

    candidate = _clean_workspace_relative_path(requested_path)

    try:
        resolved_workspace = workspace_dir.resolve(strict=True)
    except OSError as exc:
        raise MarcBotError(
            "MBOT-LLM-051",
            f"Workspace directory is not available: {workspace_dir}",
        ) from exc

    try:
        resolved_path = (resolved_workspace / candidate).resolve(strict=True)
    except OSError as exc:
        raise MarcBotError(
            "MBOT-LLM-052",
            f"Workspace summary file not found: {requested_path}",
        ) from exc

    if resolved_path != resolved_workspace and resolved_workspace not in resolved_path.parents:
        raise MarcBotError(
            "MBOT-LLM-053",
            "Resolved summary file path is outside the workspace",
        )

    if not resolved_path.is_file():
        raise MarcBotError(
            "MBOT-LLM-054",
            f"Workspace summary path is not a file: {requested_path}",
        )

    try:
        raw = resolved_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise MarcBotError(
            "MBOT-LLM-055",
            f"Workspace summary file is not valid UTF-8 text: {requested_path}",
        ) from exc
    except OSError as exc:
        raise MarcBotError(
            "MBOT-LLM-056",
            f"Unable to read workspace summary file: {requested_path}",
        ) from exc

    text = raw.strip()
    if not text:
        raise MarcBotError(
            "MBOT-LLM-057",
            f"Workspace summary file is empty: {requested_path}",
        )

    if len(text) > MAX_SUMMARY_FILE_CHARS:
        raise MarcBotError(
            "MBOT-LLM-058",
            f"Workspace summary file exceeds {MAX_SUMMARY_FILE_CHARS} characters",
        )

    return WorkspaceSummaryInput(
        requested_path=str(candidate),
        resolved_path=resolved_path,
        text=text,
    )


def build_summary_prompt(summary_input: WorkspaceSummaryInput) -> str:
    """Build a fixed prompt for summarizing a workspace file."""

    return (
        "Summarize this MarcBot text file. "
        "Return exactly 3 short bullets. "
        "Each bullet must be under 12 words. "
        "Use only the file content.\n\n"
        f"File path: {summary_input.requested_path}\n\n"
        "File content:\n"
        f"{summary_input.text}\n\n"
        "Summary:"
    )


def resolve_workspace_summary_output_path(
    requested_path: str,
    workspace_dir: Path = WORKSPACE_DIR,
) -> Path:
    """Validate and resolve a workspace-relative output path for a summary file."""

    candidate = _clean_workspace_relative_path(requested_path)

    try:
        resolved_workspace = workspace_dir.resolve(strict=True)
    except OSError as exc:
        raise MarcBotError(
            "MBOT-LLM-059",
            f"Workspace directory is not available: {workspace_dir}",
        ) from exc

    resolved_path = (resolved_workspace / candidate).resolve(strict=False)

    if resolved_path == resolved_workspace or resolved_workspace not in resolved_path.parents:
        raise MarcBotError(
            "MBOT-LLM-060",
            "Resolved summary output path is outside the workspace",
        )

    if resolved_path.exists():
        raise MarcBotError(
            "MBOT-LLM-061",
            f"Workspace summary output already exists: {requested_path}",
        )

    parent = resolved_path.parent
    if parent.exists() and not parent.is_dir():
        raise MarcBotError(
            "MBOT-LLM-062",
            f"Workspace summary output parent is not a directory: {requested_path}",
        )

    return resolved_path


def write_workspace_summary_output(
    requested_path: str,
    content: str,
    workspace_dir: Path = WORKSPACE_DIR,
) -> Path:
    """Write a generated summary to a new workspace-relative output file."""

    text = content.strip()
    if not text:
        raise MarcBotError(
            "MBOT-LLM-063",
            "Workspace summary output content must not be empty",
        )

    output_path = resolve_workspace_summary_output_path(
        requested_path,
        workspace_dir=workspace_dir,
    )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    except OSError as exc:
        raise MarcBotError(
            "MBOT-LLM-064",
            f"Unable to write workspace summary output: {requested_path}",
        ) from exc

    return output_path
