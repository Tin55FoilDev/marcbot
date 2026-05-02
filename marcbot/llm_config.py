"""LLM provider/profile configuration for MarcBot."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from marcbot.errors import MarcBotError
from marcbot.paths import CONFIG_DIR

DEFAULT_LLM_CONFIG_PATH = CONFIG_DIR / "llm-providers.toml"
SUPPORTED_PROVIDER_TYPES = ("openai_compatible", "openai")


@dataclass(frozen=True)
class LlmProviderConfig:
    """Configuration for one LLM provider."""

    name: str
    enabled: bool
    provider_type: str
    base_url: str
    api_key_env: str
    timeout_seconds: int


@dataclass(frozen=True)
class LlmProfileConfig:
    """Configuration for one named LLM profile."""

    name: str
    provider: str
    model: str
    temperature: float
    max_tokens: int
    intended_use: str


@dataclass(frozen=True)
class LlmConfig:
    """Full LLM provider/profile configuration."""

    path: Path
    providers: dict[str, LlmProviderConfig]
    profiles: dict[str, LlmProfileConfig]


def _read_toml_file(path: Path) -> dict[str, Any]:
    """Read a TOML file and return parsed data."""
    if not path.is_file():
        raise MarcBotError("MBOT-LLM-001", f"Missing LLM config file: {path}")

    try:
        with path.open("rb") as file_obj:
            data = tomllib.load(file_obj)
    except tomllib.TOMLDecodeError as exc:
        raise MarcBotError("MBOT-LLM-002", f"Invalid TOML LLM config file: {path}") from exc
    except OSError as exc:
        raise MarcBotError("MBOT-LLM-003", f"Unable to read LLM config file: {path}") from exc

    if not isinstance(data, dict):
        raise MarcBotError("MBOT-LLM-004", f"LLM config root must be a table: {path}")

    return data


def _require_table(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a required table from parsed TOML."""
    value = data.get(key)
    if not isinstance(value, dict):
        raise MarcBotError("MBOT-LLM-005", f"Missing or invalid [{key}] LLM config section")
    return value


def _require_named_table(parent: dict[str, Any], section: str, name: str) -> dict[str, Any]:
    """Return a named child table."""
    value = parent.get(name)
    if not isinstance(value, dict):
        raise MarcBotError(
            "MBOT-LLM-006",
            f"Missing or invalid LLM config section: [{section}.{name}]",
        )
    return value


def _require_nonempty_string(section: dict[str, Any], key: str, section_name: str) -> str:
    """Return a required non-empty string from a config section."""
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MarcBotError(
            "MBOT-LLM-007",
            f"Missing or invalid LLM config value: {section_name}.{key}",
        )
    return value.strip()


def _optional_nonempty_string(
    section: dict[str, Any],
    key: str,
    section_name: str,
    default: str = "",
) -> str:
    """Return an optional string from a config section."""
    value = section.get(key, default)
    if not isinstance(value, str):
        raise MarcBotError(
            "MBOT-LLM-008",
            f"LLM config value must be a string: {section_name}.{key}",
        )
    return value.strip()


def _optional_bool(section: dict[str, Any], key: str, section_name: str, default: bool) -> bool:
    """Return an optional boolean from a config section."""
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise MarcBotError(
            "MBOT-LLM-009",
            f"LLM config value must be true/false: {section_name}.{key}",
        )
    return value


def _optional_positive_int(
    section: dict[str, Any],
    key: str,
    section_name: str,
    default: int,
) -> int:
    """Return an optional positive integer from a config section."""
    value = section.get(key, default)
    if not isinstance(value, int) or value <= 0:
        raise MarcBotError(
            "MBOT-LLM-010",
            f"LLM config value must be a positive integer: {section_name}.{key}",
        )
    return value


def _optional_float(
    section: dict[str, Any],
    key: str,
    section_name: str,
    default: float,
) -> float:
    """Return an optional float from a config section."""
    value = section.get(key, default)
    if isinstance(value, int):
        value = float(value)
    if not isinstance(value, float):
        raise MarcBotError(
            "MBOT-LLM-011",
            f"LLM config value must be a number: {section_name}.{key}",
        )
    return value


def _load_provider(name: str, section: dict[str, Any]) -> LlmProviderConfig:
    """Load one provider config."""
    section_name = f"providers.{name}"
    provider_type = _require_nonempty_string(section, "type", section_name)
    if provider_type not in SUPPORTED_PROVIDER_TYPES:
        supported = ", ".join(SUPPORTED_PROVIDER_TYPES)
        raise MarcBotError(
            "MBOT-LLM-012",
            f"Unsupported LLM provider type for {section_name}: {provider_type} "
            f"(supported: {supported})",
        )

    base_url = _optional_nonempty_string(section, "base_url", section_name)
    if provider_type == "openai_compatible" and not base_url:
        raise MarcBotError(
            "MBOT-LLM-013",
            f"OpenAI-compatible provider requires base_url: {section_name}",
        )

    return LlmProviderConfig(
        name=name,
        enabled=_optional_bool(section, "enabled", section_name, True),
        provider_type=provider_type,
        base_url=base_url.rstrip("/"),
        api_key_env=_optional_nonempty_string(section, "api_key_env", section_name),
        timeout_seconds=_optional_positive_int(section, "timeout_seconds", section_name, 30),
    )


def _load_profile(name: str, section: dict[str, Any]) -> LlmProfileConfig:
    """Load one profile config."""
    section_name = f"profiles.{name}"
    return LlmProfileConfig(
        name=name,
        provider=_require_nonempty_string(section, "provider", section_name),
        model=_require_nonempty_string(section, "model", section_name),
        temperature=_optional_float(section, "temperature", section_name, 0.2),
        max_tokens=_optional_positive_int(section, "max_tokens", section_name, 500),
        intended_use=_optional_nonempty_string(section, "intended_use", section_name),
    )


def load_llm_config(path: Path = DEFAULT_LLM_CONFIG_PATH) -> LlmConfig:
    """Load and validate LLM provider/profile configuration."""
    data = _read_toml_file(path)

    providers_table = _require_table(data, "providers")
    profiles_table = _require_table(data, "profiles")

    providers: dict[str, LlmProviderConfig] = {}
    for name in sorted(providers_table):
        provider_section = _require_named_table(providers_table, "providers", name)
        providers[name] = _load_provider(name, provider_section)

    if not providers:
        raise MarcBotError("MBOT-LLM-014", "LLM config must define at least one provider")

    profiles: dict[str, LlmProfileConfig] = {}
    for name in sorted(profiles_table):
        profile_section = _require_named_table(profiles_table, "profiles", name)
        profile = _load_profile(name, profile_section)
        if profile.provider not in providers:
            raise MarcBotError(
                "MBOT-LLM-015",
                f"LLM profile references unknown provider: profiles.{name}.provider",
            )
        profiles[name] = profile

    if not profiles:
        raise MarcBotError("MBOT-LLM-016", "LLM config must define at least one profile")

    return LlmConfig(path=path, providers=providers, profiles=profiles)


def format_llm_profiles(config: LlmConfig) -> str:
    """Format configured LLM profiles for operator output."""
    lines = [
        "MarcBot LLM profiles",
        f"Config: {config.path}",
        "",
    ]

    for profile in config.profiles.values():
        provider = config.providers[profile.provider]
        provider_state = "enabled" if provider.enabled else "disabled"
        lines.append(f"- {profile.name}")
        lines.append(
            f"  - provider: {profile.provider} "
            f"({provider.provider_type}, {provider_state})"
        )
        lines.append(f"  - model: {profile.model}")
        lines.append(f"  - max_tokens: {profile.max_tokens}")
        lines.append(f"  - temperature: {profile.temperature:g}")
        if profile.intended_use:
            lines.append(f"  - intended_use: {profile.intended_use}")

    return "\n".join(lines)
