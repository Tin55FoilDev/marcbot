"""Read-only LLM status formatting for MarcBot."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from marcbot.errors import MarcBotError
from marcbot.llm_client import (
    LlmHealthResult,
    format_llm_health_result,
    run_openai_compatible_health_check,
)
from marcbot.llm_config import (
    DEFAULT_LLM_CONFIG_PATH,
    LlmConfig,
    load_llm_config,
)
from marcbot.paths import CONFIG_DIR

DEFAULT_LLM_ENV_PATH = CONFIG_DIR / "llm.env"
DEFAULT_HEALTH_PROFILE = "local_fast"

HealthRunner = Callable[..., LlmHealthResult]


def load_llm_env(path: Path = DEFAULT_LLM_ENV_PATH) -> dict[str, str]:
    """Load a small KEY=VALUE env file for LLM provider secrets."""
    if not path.exists():
        raise MarcBotError(
            "MBOT-LLM-038",
            f"LLM env file does not exist: {path}",
        )

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            raise MarcBotError(
                "MBOT-LLM-039",
                f"Invalid LLM env line {line_number}: expected KEY=VALUE",
            )

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\'").strip('\"')

        if not key:
            raise MarcBotError(
                "MBOT-LLM-040",
                f"Invalid LLM env line {line_number}: empty key",
            )

        values[key] = value

    return values


def _with_env_values(
    values: dict[str, str],
    func: Callable[[], LlmHealthResult],
) -> LlmHealthResult:
    """Run a function with temporary environment values."""
    previous: dict[str, str | None] = {key: os.environ.get(key) for key in values}

    try:
        os.environ.update(values)
        return func()
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def _format_profiles(config: LlmConfig) -> list[str]:
    """Format configured profiles for Telegram status."""
    lines = [
        f"Profiles: {len(config.profiles)}",
    ]

    for profile_name in sorted(config.profiles):
        profile = config.profiles[profile_name]
        provider = config.providers[profile.provider]
        state = "enabled" if provider.enabled else "disabled"
        lines.append(
            f"- {profile.name}: {profile.model} "
            f"via {provider.name} ({provider.provider_type}, {state})"
        )

    return lines


def format_llm_status_message(
    *,
    config_path: Path = DEFAULT_LLM_CONFIG_PATH,
    env_path: Path = DEFAULT_LLM_ENV_PATH,
    health_profile: str = DEFAULT_HEALTH_PROFILE,
    health_runner: HealthRunner = run_openai_compatible_health_check,
) -> str:
    """Return a bounded read-only LLM status message for Telegram."""
    config = load_llm_config(config_path)

    lines = ["🤖 MarcBot LLM status", "", *_format_profiles(config), "", "Health check:"]

    profile = config.profiles.get(health_profile)
    if profile is None:
        lines.append("Status: unavailable")
        lines.append(f"Reason: profile not configured: {health_profile}")
        return "\n".join(lines)

    provider = config.providers[profile.provider]

    try:
        env_values = load_llm_env(env_path)
        health_result = _with_env_values(
            env_values,
            lambda: health_runner(
                provider=provider,
                profile_name=profile.name,
                model=profile.model,
            ),
        )
    except MarcBotError as exc:
        lines.append(f"Profile: {health_profile}")
        lines.append("Status: error")
        lines.append(f"Error: [{exc.code}] {exc.message}")
        return "\n".join(lines)

    health_lines = format_llm_health_result(health_result).splitlines()
    for line in health_lines[1:]:
        lines.append(line)

    return "\n".join(lines)
