import pytest

from marcbot.errors import MarcBotError
from marcbot.llm_file_summary import (
    MAX_SUMMARY_FILE_CHARS,
    build_summary_prompt,
    load_workspace_summary_input,
)


def test_load_workspace_summary_input(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    report = workspace / "reports" / "daily.md"
    report.parent.mkdir()
    report.write_text("MarcBot report content", encoding="utf-8")

    result = load_workspace_summary_input("reports/daily.md", workspace_dir=workspace)

    assert result.requested_path == "reports/daily.md"
    assert result.resolved_path == report
    assert result.text == "MarcBot report content"


def test_load_workspace_summary_input_rejects_empty_path(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(MarcBotError) as excinfo:
        load_workspace_summary_input("", workspace_dir=workspace)

    assert excinfo.value.code == "MBOT-LLM-048"


def test_load_workspace_summary_input_rejects_absolute_path(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(MarcBotError) as excinfo:
        load_workspace_summary_input("/tmp/report.md", workspace_dir=workspace)

    assert excinfo.value.code == "MBOT-LLM-049"


def test_load_workspace_summary_input_rejects_parent_traversal(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(MarcBotError) as excinfo:
        load_workspace_summary_input("../secret.txt", workspace_dir=workspace)

    assert excinfo.value.code == "MBOT-LLM-050"


def test_load_workspace_summary_input_rejects_missing_file(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(MarcBotError) as excinfo:
        load_workspace_summary_input("missing.md", workspace_dir=workspace)

    assert excinfo.value.code == "MBOT-LLM-052"


def test_load_workspace_summary_input_rejects_directory(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "reports").mkdir()

    with pytest.raises(MarcBotError) as excinfo:
        load_workspace_summary_input("reports", workspace_dir=workspace)

    assert excinfo.value.code == "MBOT-LLM-054"


def test_load_workspace_summary_input_rejects_empty_file(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    report = workspace / "empty.md"
    report.write_text("   ", encoding="utf-8")

    with pytest.raises(MarcBotError) as excinfo:
        load_workspace_summary_input("empty.md", workspace_dir=workspace)

    assert excinfo.value.code == "MBOT-LLM-057"


def test_load_workspace_summary_input_rejects_oversized_file(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    report = workspace / "large.md"
    report.write_text("x" * (MAX_SUMMARY_FILE_CHARS + 1), encoding="utf-8")

    with pytest.raises(MarcBotError) as excinfo:
        load_workspace_summary_input("large.md", workspace_dir=workspace)

    assert excinfo.value.code == "MBOT-LLM-058"


def test_build_summary_prompt(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    report = workspace / "daily.md"
    report.write_text("MarcBot report content", encoding="utf-8")
    summary_input = load_workspace_summary_input("daily.md", workspace_dir=workspace)

    prompt = build_summary_prompt(summary_input)

    assert "Summarize this MarcBot text file" in prompt
    assert "Return exactly 3 short bullets" in prompt
    assert "File path: daily.md" in prompt
    assert "MarcBot report content" in prompt
    assert "Summary:" in prompt
