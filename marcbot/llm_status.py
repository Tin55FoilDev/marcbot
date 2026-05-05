"""Read-only LLM status formatting for MarcBot."""

from __future__ import annotations

from pathlib import Path

from marcbot.errors import MarcBotError
from marcbot.llm_config import (
    DEFAULT_LLM_CONFIG_PATH,
    LlmConfig,
    load_llm_config,
)
from marcbot.paths import CONFIG_DIR

DEFAULT_LLM_ENV_PATH = CONFIG_DIR / "llm.env"


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
        value = value.strip().strip("'").strip("\"")

        if not key:
            raise MarcBotError(
                "MBOT-LLM-040",
                f"Invalid LLM env line {line_number}: empty key",
            )

        values[key] = value

    return values


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
) -> str:
    """Return a bounded read-only LLM status message for Telegram."""
    config = load_llm_config(config_path)

    lines = [
        "🤖 MarcBot LLM status",
        "",
        *_format_profiles(config),
        "",
        "Provider contact: not performed",
        "Health checks: CLI-only via python -m marcbot llm health <profile>",
    ]

    return "\n".join(lines)
