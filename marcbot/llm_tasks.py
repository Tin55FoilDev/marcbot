"""LLM task-to-profile mapping helpers for MarcBot."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from marcbot.errors import MarcBotError

DEFAULT_LLM_TASKS_CONFIG_PATH = Path("/srv/marcbot/config/llm-tasks.toml")
_TASK_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class LlmTaskProfile:
    """Configured mapping from a MarcBot task name to an LLM profile."""

    name: str
    profile: str
    description: str


@dataclass(frozen=True)
class LlmTaskConfig:
    """Loaded LLM task mapping config."""

    tasks: dict[str, LlmTaskProfile]


def _require_mapping(value: Any, code: str, message: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MarcBotError(code, message)
    return value


def _validate_task_name(name: str) -> None:
    if not _TASK_NAME_RE.fullmatch(name):
        raise MarcBotError(
            "MBOT-LLM-043",
            f"Invalid LLM task name: {name}",
        )


def load_llm_task_config(
    path: Path = DEFAULT_LLM_TASKS_CONFIG_PATH,
) -> LlmTaskConfig:
    """Load LLM task-to-profile mappings from TOML."""

    if not path.exists():
        raise MarcBotError(
            "MBOT-LLM-041",
            f"LLM task config not found: {path}",
        )

    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise MarcBotError(
            "MBOT-LLM-042",
            f"Invalid LLM task config TOML: {path}: {exc}",
        ) from exc

    root = _require_mapping(raw, "MBOT-LLM-042", "Invalid LLM task config root")
    raw_tasks = _require_mapping(
        root.get("tasks", {}),
        "MBOT-LLM-042",
        "Invalid LLM task config: tasks must be a table",
    )

    tasks: dict[str, LlmTaskProfile] = {}
    for task_name, task_data in raw_tasks.items():
        _validate_task_name(task_name)
        task_table = _require_mapping(
            task_data,
            "MBOT-LLM-042",
            f"Invalid LLM task config for task: {task_name}",
        )

        profile = task_table.get("profile")
        if not isinstance(profile, str) or not profile.strip():
            raise MarcBotError(
                "MBOT-LLM-044",
                f"LLM task {task_name} must define a non-empty profile",
            )

        description = task_table.get("description", "")
        if description is None:
            description = ""
        if not isinstance(description, str):
            raise MarcBotError(
                "MBOT-LLM-045",
                f"LLM task {task_name} description must be a string",
            )

        tasks[task_name] = LlmTaskProfile(
            name=task_name,
            profile=profile.strip(),
            description=description.strip(),
        )

    return LlmTaskConfig(tasks=tasks)


def format_llm_tasks(config: LlmTaskConfig) -> str:
    """Format loaded LLM task mappings for CLI output."""

    lines = ["MarcBot LLM tasks"]
    if not config.tasks:
        lines.append("No LLM tasks configured.")
        return "\n".join(lines)

    for task_name in sorted(config.tasks):
        task = config.tasks[task_name]
        line = f"- {task.name}: profile={task.profile}"
        if task.description:
            line += f" — {task.description}"
        lines.append(line)

    return "\n".join(lines)


def format_llm_task_detail(task: LlmTaskProfile) -> str:
    """Format one LLM task mapping for CLI output."""

    lines = [
        "MarcBot LLM task",
        f"Name: {task.name}",
        f"Profile: {task.profile}",
    ]
    if task.description:
        lines.append(f"Description: {task.description}")
    return "\n".join(lines)
