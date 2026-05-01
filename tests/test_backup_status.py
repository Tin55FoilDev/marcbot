"""Tests for MarcBot backup status helpers."""

from pathlib import Path

from marcbot.backup_status import (
    BackupStatus,
    format_backup_status_message,
    get_backup_status,
    parse_backup_marker,
)


def write_marker(
    marker_file: Path,
    *,
    archive: Path,
    sha: Path,
    created_epoch: int = 1000,
    size_bytes: int = 5,
) -> None:
    """Write a test latest-backup.txt marker."""
    marker_file.write_text(
        "\n".join(
            [
                "name=marcbot-backup-test.tar.gz",
                f"path={archive}",
                f"sha256_path={sha}",
                "created_iso=2026-04-30T22:15:00-04:00",
                f"created_epoch={created_epoch}",
                f"size_bytes={size_bytes}",
                "retention_days=14",
                "",
            ],
        ),
        encoding="utf-8",
    )


def test_parse_backup_marker(tmp_path: Path) -> None:
    archive = tmp_path / "backup.tar.gz"
    sha = tmp_path / "backup.tar.gz.sha256"
    marker_file = tmp_path / "latest-backup.txt"
    write_marker(marker_file, archive=archive, sha=sha)

    marker = parse_backup_marker(marker_file)

    assert marker.name == "marcbot-backup-test.tar.gz"
    assert marker.path == archive
    assert marker.sha256_path == sha
    assert marker.created_epoch == 1000
    assert marker.size_bytes == 5
    assert marker.retention_days == 14


def test_get_backup_status_missing_marker(tmp_path: Path) -> None:
    status = get_backup_status(tmp_path / "missing.txt")

    assert not status.ok
    assert status.marker is None
    assert "latest marker missing" in status.messages[0]


def test_get_backup_status_malformed_marker(tmp_path: Path) -> None:
    marker_file = tmp_path / "latest-backup.txt"
    marker_file.write_text("name=backup.tar.gz\n", encoding="utf-8")

    status = get_backup_status(marker_file)

    assert not status.ok
    assert status.marker is None
    assert "unable to parse latest marker" in status.messages[0]


def test_get_backup_status_healthy(tmp_path: Path) -> None:
    archive = tmp_path / "backup.tar.gz"
    archive.write_text("hello", encoding="utf-8")
    sha = tmp_path / "backup.tar.gz.sha256"
    sha.write_text("checksum  backup.tar.gz\n", encoding="utf-8")
    marker_file = tmp_path / "latest-backup.txt"
    write_marker(marker_file, archive=archive, sha=sha, created_epoch=1000, size_bytes=5)

    status = get_backup_status(marker_file, now_epoch=1100)

    assert status.ok
    assert status.marker is not None
    assert "OK: archive present" in status.messages
    assert "OK: checksum present" in status.messages


def test_get_backup_status_missing_archive(tmp_path: Path) -> None:
    archive = tmp_path / "missing.tar.gz"
    sha = tmp_path / "missing.tar.gz.sha256"
    sha.write_text("checksum  missing.tar.gz\n", encoding="utf-8")
    marker_file = tmp_path / "latest-backup.txt"
    write_marker(marker_file, archive=archive, sha=sha)

    status = get_backup_status(marker_file, now_epoch=1100)

    assert not status.ok
    assert any("archive missing" in message for message in status.messages)


def test_get_backup_status_missing_checksum(tmp_path: Path) -> None:
    archive = tmp_path / "backup.tar.gz"
    archive.write_text("hello", encoding="utf-8")
    sha = tmp_path / "missing.sha256"
    marker_file = tmp_path / "latest-backup.txt"
    write_marker(marker_file, archive=archive, sha=sha, size_bytes=5)

    status = get_backup_status(marker_file, now_epoch=1100)

    assert not status.ok
    assert any("checksum missing" in message for message in status.messages)


def test_get_backup_status_old_backup_warns(tmp_path: Path) -> None:
    archive = tmp_path / "backup.tar.gz"
    archive.write_text("hello", encoding="utf-8")
    sha = tmp_path / "backup.tar.gz.sha256"
    sha.write_text("checksum  backup.tar.gz\n", encoding="utf-8")
    marker_file = tmp_path / "latest-backup.txt"
    write_marker(marker_file, archive=archive, sha=sha, created_epoch=1000, size_bytes=5)

    status = get_backup_status(marker_file, now_epoch=2000, max_age_seconds=100)

    assert not status.ok
    assert any("latest backup is old" in message for message in status.messages)


def test_format_backup_status_message_missing_marker() -> None:
    status = BackupStatus(
        ok=False,
        marker=None,
        messages=("ERROR: latest marker missing",),
    )

    message = format_backup_status_message(status)

    assert "🤖 MarcBot backup status" in message
    assert "ERROR: latest marker missing" in message
    assert "Overall: unhealthy" in message


def test_format_backup_status_message_healthy(tmp_path: Path) -> None:
    archive = tmp_path / "backup.tar.gz"
    archive.write_text("hello", encoding="utf-8")
    sha = tmp_path / "backup.tar.gz.sha256"
    sha.write_text("checksum  backup.tar.gz\n", encoding="utf-8")
    marker_file = tmp_path / "latest-backup.txt"
    write_marker(marker_file, archive=archive, sha=sha, created_epoch=1000, size_bytes=5)

    status = get_backup_status(marker_file, now_epoch=1100)
    message = format_backup_status_message(status)

    assert "🤖 MarcBot backup status" in message
    assert "Latest backup: marcbot-backup-test.tar.gz" in message
    assert "Size: 5 B" in message
    assert "Overall: healthy" in message
