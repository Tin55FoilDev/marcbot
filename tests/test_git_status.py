"""Tests for MarcBot Git status helpers."""

from pathlib import Path

from marcbot.git_status import GitStatus, format_git_report


def test_format_git_report_clean() -> None:
    status = GitStatus(
        repo_path=Path("/srv/marcbot/app"),
        branch="main",
        commit="abc1234",
        dirty=False,
    )

    report = format_git_report(status)

    assert report == (
        "🤖 MarcBot git\n"
        "Repo: /srv/marcbot/app\n"
        "Branch: main\n"
        "Commit: abc1234\n"
        "Status: clean"
    )


def test_format_git_report_dirty() -> None:
    status = GitStatus(
        repo_path=Path("/srv/marcbot/app"),
        branch="main",
        commit="abc1234",
        dirty=True,
    )

    report = format_git_report(status)

    assert "Status: dirty" in report
