"""Read-only Git status helpers for MarcBot."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from marcbot.paths import APP_DIR

GIT_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class GitStatus:
    """Read-only Git status for the MarcBot application repository."""

    repo_path: Path
    branch: str
    commit: str
    dirty: bool


def _run_git(repo_path: Path, args: list[str]) -> str:
    """Run a fixed git query in the MarcBot app repo and return compact output."""
    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
    )

    output = (result.stdout or result.stderr).strip()
    if not output:
        return "unknown"

    return output.splitlines()[0].strip() or "unknown"


def get_git_status(repo_path: Path = APP_DIR) -> GitStatus:
    """Return branch, commit, and dirty/clean status for the MarcBot repo."""
    branch = _run_git(repo_path, ["branch", "--show-current"])
    commit = _run_git(repo_path, ["rev-parse", "--short", "HEAD"])
    porcelain = subprocess.run(
        ["git", "-C", str(repo_path), "status", "--porcelain"],
        check=False,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
    )

    dirty = bool(porcelain.stdout.strip())

    return GitStatus(
        repo_path=repo_path,
        branch=branch,
        commit=commit,
        dirty=dirty,
    )


def format_git_report(status: GitStatus | None = None) -> str:
    """Format a Telegram-friendly Git status report."""
    if status is None:
        status = get_git_status()

    repo_state = "dirty" if status.dirty else "clean"

    return (
        "🤖 MarcBot git\n"
        f"Repo: {status.repo_path}\n"
        f"Branch: {status.branch}\n"
        f"Commit: {status.commit}\n"
        f"Status: {repo_state}"
    )
