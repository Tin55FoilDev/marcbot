from __future__ import annotations

from pathlib import Path

from marcbot.memory_store import (
    MEMORY_SUBDIRS,
    format_memory_status_message,
    get_memory_status,
    init_memory_store,
)


def test_init_memory_store_creates_expected_layout(tmp_path: Path) -> None:
    result = init_memory_store(root=tmp_path)

    assert result.root == tmp_path
    assert tmp_path.is_dir()
    assert (tmp_path / "README.md").is_file()
    for name in MEMORY_SUBDIRS:
        assert (tmp_path / name).is_dir()

    assert "MarcBot memory initialized:" in result.message


def test_init_memory_store_is_idempotent(tmp_path: Path) -> None:
    first = init_memory_store(root=tmp_path)
    second = init_memory_store(root=tmp_path)

    assert first.created
    assert second.created == ()
    assert second.message == f"MarcBot memory already initialized: {tmp_path}"


def test_get_memory_status_reports_missing_store(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    status = get_memory_status(root=root)

    assert status.initialized is False
    assert status.readme_exists is False
    assert all(value is False for value in status.directories.values())
    assert status.event_files == 0


def test_get_memory_status_counts_files(tmp_path: Path) -> None:
    init_memory_store(root=tmp_path)

    (tmp_path / "events" / "2026-05.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / "facts" / "weather.toml").write_text("statement = 'x'", encoding="utf-8")
    (tmp_path / "summaries" / "summary.md").write_text("# Summary", encoding="utf-8")
    (tmp_path / "pending" / "proposal.json").write_text("{}", encoding="utf-8")
    (tmp_path / "corrections" / "corrections.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / "exports" / "export.txt").write_text("export", encoding="utf-8")

    status = get_memory_status(root=tmp_path)

    assert status.initialized is True
    assert status.event_files == 1
    assert status.fact_files == 1
    assert status.summary_files == 1
    assert status.pending_files == 1
    assert status.correction_files == 1
    assert status.export_files == 1


def test_format_memory_status_message(tmp_path: Path) -> None:
    init_memory_store(root=tmp_path)

    message = format_memory_status_message(root=tmp_path)

    assert "MarcBot memory" in message
    assert f"Root: {tmp_path}" in message
    assert "Initialized: yes" in message
    assert "- events: present" in message
    assert "- pending proposals: 0" in message
    assert "Provider contact: no" in message
