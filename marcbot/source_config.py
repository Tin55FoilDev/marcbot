"""Allowlisted source monitor configuration loading and validation."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from marcbot.errors import MarcBotError

DEFAULT_SOURCE_CONFIG_PATH = Path("/srv/marcbot/config/sources.toml")

_ALLOWED_SOURCE_KINDS = frozenset(
    {
        "github_releases",
        "web_page",
    },
)

_SOURCE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class SourceDefinition:
    """One allowlisted source definition."""

    name: str
    kind: str
    url: str
    enabled: bool = True


@dataclass(frozen=True)
class SourceConfig:
    """Loaded source monitor configuration."""

    path: Path
    exists: bool
    sources: tuple[SourceDefinition, ...]


def _require_string(value: object, field_name: str, source_index: int) -> str:
    """Return a required non-empty string field."""
    if not isinstance(value, str) or not value.strip():
        raise MarcBotError(
            "MBOT-SOURCE-002",
            f"Source #{source_index} has invalid or missing {field_name}",
        )
    return value.strip()


def _validate_source_name(name: str, source_index: int) -> None:
    """Validate a source name slug."""
    if not _SOURCE_NAME_RE.fullmatch(name):
        raise MarcBotError(
            "MBOT-SOURCE-003",
            (
                f"Source #{source_index} has invalid name: {name}. "
                "Use lowercase letters, numbers, underscores, or hyphens only."
            ),
        )


def _validate_source_kind(kind: str, source_index: int) -> None:
    """Validate the allowlisted source kind."""
    if kind not in _ALLOWED_SOURCE_KINDS:
        allowed = ", ".join(sorted(_ALLOWED_SOURCE_KINDS))
        raise MarcBotError(
            "MBOT-SOURCE-004",
            f"Source #{source_index} has invalid kind: {kind}. Allowed kinds: {allowed}",
        )


def _validate_source_url(url: str, source_index: int) -> None:
    """Validate that a source URL is HTTPS."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise MarcBotError(
            "MBOT-SOURCE-005",
            f"Source #{source_index} has invalid url: only https:// URLs are allowed",
        )


def _load_toml(path: Path) -> dict[str, object]:
    """Load TOML from path."""
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except tomllib.TOMLDecodeError as exc:
        raise MarcBotError(
            "MBOT-SOURCE-006",
            f"Invalid source config TOML: {path}",
        ) from exc
    except OSError as exc:
        raise MarcBotError(
            "MBOT-SOURCE-007",
            f"Unable to read source config: {path}",
        ) from exc

    if not isinstance(data, dict):
        raise MarcBotError("MBOT-SOURCE-008", "Source config root must be a TOML table")

    return data


def load_source_config(path: Path = DEFAULT_SOURCE_CONFIG_PATH) -> SourceConfig:
    """Load and validate source monitor config.

    Missing config is treated as a clean empty source list so the source monitor
    can be installed before sources are configured.
    """
    if not path.exists():
        return SourceConfig(path=path, exists=False, sources=())

    data = _load_toml(path)
    raw_sources = data.get("sources", [])

    if not isinstance(raw_sources, list):
        raise MarcBotError(
            "MBOT-SOURCE-001",
            "Source config must contain zero or more [[sources]] tables",
        )

    sources: list[SourceDefinition] = []
    seen_names: set[str] = set()

    for index, raw_source in enumerate(raw_sources, start=1):
        if not isinstance(raw_source, dict):
            raise MarcBotError(
                "MBOT-SOURCE-009",
                f"Source #{index} must be a TOML table",
            )

        name = _require_string(raw_source.get("name"), "name", index)
        kind = _require_string(raw_source.get("kind"), "kind", index)
        url = _require_string(raw_source.get("url"), "url", index)
        enabled = raw_source.get("enabled", True)

        if not isinstance(enabled, bool):
            raise MarcBotError(
                "MBOT-SOURCE-010",
                f"Source #{index} has invalid enabled value: use true or false",
            )

        _validate_source_name(name, index)
        _validate_source_kind(kind, index)
        _validate_source_url(url, index)

        if name in seen_names:
            raise MarcBotError(
                "MBOT-SOURCE-011",
                f"Duplicate source name: {name}",
            )
        seen_names.add(name)

        sources.append(
            SourceDefinition(
                name=name,
                kind=kind,
                url=url,
                enabled=enabled,
            ),
        )

    return SourceConfig(path=path, exists=True, sources=tuple(sources))


def format_source_config_summary(config: SourceConfig) -> str:
    """Format a human-readable source config summary."""
    lines = [
        "MarcBot source monitor config",
        f"Path: {config.path}",
        f"Exists: {str(config.exists).lower()}",
        f"Sources: {len(config.sources)}",
    ]

    if not config.sources:
        lines.append("No sources configured.")
        return "\n".join(lines)

    lines.append("")
    for source in config.sources:
        state = "enabled" if source.enabled else "disabled"
        lines.append(f"- {source.name} [{source.kind}, {state}]")
        lines.append(f"  {source.url}")

    return "\n".join(lines)
