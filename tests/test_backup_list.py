"""Tests for MarcBot backup listing."""

import os
from datetime import UTC, datetime, timedelta

from marcbot.backup_list import format_backup_list_message, list_recent_backups


def test_backup_list_reports_missing_directory(tmp_path) -> None:
    missing = tmp_path / "missing"

    message = format_backup_list_message(
        backup_dir=missing,
        now=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
    )

    assert "🤖 MarcBot backup list" in message
    assert "Recent app-level backups: none" in message
    assert "backup directory is missing" in message


def test_backup_list_reports_no_archives(tmp_path) -> None:
    message = format_backup_list_message(
        backup_dir=tmp_path,
        now=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
    )

    assert "Recent app-level backups: none" in message
    assert "no backup archives found" in message


def test_list_recent_backups_sorts_newest_first_and_limits(tmp_path) -> None:
    base_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)

    older = tmp_path / "marcbot-backup-20260430-233000.tar.gz"
    newer = tmp_path / "marcbot-backup-20260501-233000.tar.gz"
    ignored = tmp_path / "other-file.tar.gz"

    older.write_text("older\n", encoding="utf-8")
    newer.write_text("newer\n", encoding="utf-8")
    ignored.write_text("ignored\n", encoding="utf-8")

    older_ts = (base_time - timedelta(days=1)).timestamp()
    newer_ts = base_time.timestamp()

    os.utime(older, (older_ts, older_ts))
    os.utime(newer, (newer_ts, newer_ts))

    entries = list_recent_backups(backup_dir=tmp_path, limit=1)

    assert len(entries) == 1
    assert entries[0].path == newer


def test_backup_list_reports_latest_backup_with_checksum(tmp_path) -> None:
    now = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    backup = tmp_path / "marcbot-backup-20260501-110000.tar.gz"
    checksum = tmp_path / "marcbot-backup-20260501-110000.tar.gz.sha256"

    backup.write_text("backup\n", encoding="utf-8")
    checksum.write_text("checksum\n", encoding="utf-8")

    backup_ts = (now - timedelta(hours=1)).timestamp()
    os.utime(backup, (backup_ts, backup_ts))
    os.utime(checksum, (backup_ts, backup_ts))

    message = format_backup_list_message(backup_dir=tmp_path, now=now)

    assert "marcbot-backup-20260501-110000.tar.gz" in message
    assert "SHA256: present" in message
    assert "Age: 1 hour" in message
    assert "Overall: healthy" in message


def test_backup_list_warns_when_checksum_missing(tmp_path) -> None:
    now = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    backup = tmp_path / "marcbot-backup-20260501-110000.tar.gz"

    backup.write_text("backup\n", encoding="utf-8")

    backup_ts = (now - timedelta(hours=1)).timestamp()
    os.utime(backup, (backup_ts, backup_ts))

    message = format_backup_list_message(backup_dir=tmp_path, now=now)

    assert "SHA256: missing" in message
    assert "warning - one or more checksum files are missing" in message
