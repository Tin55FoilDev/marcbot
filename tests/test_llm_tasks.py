from pathlib import Path

import pytest

from marcbot.errors import MarcBotError
from marcbot.llm_tasks import (
    format_llm_task_detail,
    format_llm_tasks,
    load_llm_task_config,
)


def write_tasks_config(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_load_llm_task_config(tmp_path) -> None:
    config_path = write_tasks_config(
        tmp_path / "llm-tasks.toml",
        """
[tasks.report_summary]
profile = "local_fast"
description = "Summarize reports locally"
""",
    )

    config = load_llm_task_config(config_path)

    task = config.tasks["report_summary"]
    assert task.name == "report_summary"
    assert task.profile == "local_fast"
    assert task.description == "Summarize reports locally"


def test_load_llm_task_config_missing_file(tmp_path) -> None:
    with pytest.raises(MarcBotError) as excinfo:
        load_llm_task_config(tmp_path / "missing.toml")

    assert excinfo.value.code == "MBOT-LLM-041"


def test_load_llm_task_config_rejects_invalid_task_name(tmp_path) -> None:
    config_path = write_tasks_config(
        tmp_path / "llm-tasks.toml",
        """
[tasks."Bad Name"]
profile = "local_fast"
""",
    )

    with pytest.raises(MarcBotError) as excinfo:
        load_llm_task_config(config_path)

    assert excinfo.value.code == "MBOT-LLM-043"


def test_load_llm_task_config_requires_profile(tmp_path) -> None:
    config_path = write_tasks_config(
        tmp_path / "llm-tasks.toml",
        """
[tasks.report_summary]
description = "Missing profile"
""",
    )

    with pytest.raises(MarcBotError) as excinfo:
        load_llm_task_config(config_path)

    assert excinfo.value.code == "MBOT-LLM-044"


def test_format_llm_tasks(tmp_path) -> None:
    config = load_llm_task_config(
        write_tasks_config(
            tmp_path / "llm-tasks.toml",
            """
[tasks.report_summary]
profile = "local_fast"
description = "Summarize reports locally"
""",
        )
    )

    output = format_llm_tasks(config)

    assert "MarcBot LLM tasks" in output
    assert "- report_summary: profile=local_fast" in output
    assert "Summarize reports locally" in output


def test_format_llm_task_detail(tmp_path) -> None:
    config = load_llm_task_config(
        write_tasks_config(
            tmp_path / "llm-tasks.toml",
            """
[tasks.report_summary]
profile = "local_fast"
description = "Summarize reports locally"
""",
        )
    )

    output = format_llm_task_detail(config.tasks["report_summary"])

    assert "MarcBot LLM task" in output
    assert "Name: report_summary" in output
    assert "Profile: local_fast" in output
    assert "Description: Summarize reports locally" in output
