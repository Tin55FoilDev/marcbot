"""Tests for MarcBot disk helpers."""

from pathlib import Path

from marcbot.disk import DiskUsage, format_bytes, format_disk_usage_line


def test_format_bytes_bytes() -> None:
    assert format_bytes(512) == "512 B"


def test_format_bytes_kib() -> None:
    assert format_bytes(2048) == "2.0 KiB"


def test_format_bytes_gib() -> None:
    assert format_bytes(3 * 1024 * 1024 * 1024) == "3.0 GiB"


def test_disk_usage_percent_used() -> None:
    usage = DiskUsage(
        path=Path("/"),
        total_bytes=100,
        used_bytes=25,
        free_bytes=75,
    )

    assert usage.percent_used == 25.0


def test_disk_usage_percent_used_handles_zero_total() -> None:
    usage = DiskUsage(
        path=Path("/"),
        total_bytes=0,
        used_bytes=0,
        free_bytes=0,
    )

    assert usage.percent_used == 0.0


def test_format_disk_usage_line() -> None:
    usage = DiskUsage(
        path=Path("/"),
        total_bytes=100 * 1024 * 1024,
        used_bytes=25 * 1024 * 1024,
        free_bytes=75 * 1024 * 1024,
    )

    line = format_disk_usage_line("Root filesystem", usage)

    assert line == (
        "Root filesystem: 25.0 MiB used / 100.0 MiB total "
        "(25.0% used, 75.0 MiB free)"
    )
