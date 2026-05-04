"""Source monitor project configuration loading and validation."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from marcbot.errors import MarcBotError

CONFIG_DIR = Path("/srv/marcbot/config")
SOURCE_PROJECTS_CONFIG_DIR = CONFIG_DIR / "source-projects"
DEFAULT_SOURCE_PROJECT_NAME = "ai"
DEFAULT_SOURCE_CONFIG_PATH = (
    SOURCE_PROJECTS_CONFIG_DIR / DEFAULT_SOURCE_PROJECT_NAME / "sources.toml"
)

SUPPORTED_SOURCE_KINDS = frozenset({"github_releases", "rss_feed", "web_page"})

_SOURCE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_PROJECT_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class SourceDefinition:
    """One allowlisted source definition."""

    name: str
    kind: str
    url: str
    enabled: bool = True


@dataclass(frozen=True)
class SourceConfig:
    """Validated source monitor config for one source project."""

    path: Path
    exists: bool
    sources: tuple[SourceDefinition, ...]
    project_name: str = DEFAULT_SOURCE_PROJECT_NAME


def _source_error(code: str, message: str) -> MarcBotError:
    try:
        return MarcBotError(message, code=code)
    except TypeError:
        try:
            return MarcBotError(code, message)
        except TypeError:
            return MarcBotError(message)


def validate_source_project_name(project_name: str) -> str:
    """Validate and return a safe source project name."""
    if not isinstance(project_name, str) or not _PROJECT_NAME_RE.fullmatch(project_name):
        raise _source_error(
            "MBOT-SOURCE-011",
            "Invalid source project name. Use lowercase letters, numbers, underscores, or hyphens.",
        )
    return project_name


def source_config_path(project_name: str = DEFAULT_SOURCE_PROJECT_NAME) -> Path:
    """Return the config path for a validated source project name."""
    safe_project = validate_source_project_name(project_name)
    return SOURCE_PROJECTS_CONFIG_DIR / safe_project / "sources.toml"


def source_reports_dir(project_name: str = DEFAULT_SOURCE_PROJECT_NAME) -> Path:
    """Return the reports directory for a validated source project name."""
    safe_project = validate_source_project_name(project_name)
    return Path("/srv/marcbot/workspace/source-projects") / safe_project / "reports"


def source_summaries_dir(project_name: str = DEFAULT_SOURCE_PROJECT_NAME) -> Path:
    """Return the summaries directory for a validated source project name."""
    safe_project = validate_source_project_name(project_name)
    return Path("/srv/marcbot/workspace/source-projects") / safe_project / "summaries"


def _validate_source_name(name: Any) -> str:
    if not isinstance(name, str) or not _SOURCE_NAME_RE.fullmatch(name):
        raise _source_error(
            "MBOT-SOURCE-003",
            "Invalid source name. Use lowercase letters, numbers, underscores, or hyphens.",
        )
    return name


def _validate_source_kind(kind: Any) -> str:
    if not isinstance(kind, str) or kind not in SUPPORTED_SOURCE_KINDS:
        allowed = ", ".join(sorted(SUPPORTED_SOURCE_KINDS))
        raise _source_error("MBOT-SOURCE-004", f"Invalid source kind. Allowed kinds: {allowed}")
    return kind


def _validate_source_url(url: Any) -> str:
    if not isinstance(url, str) or not url.startswith("https://"):
        raise _source_error(
            "MBOT-SOURCE-005",
            "Invalid source URL. Only https:// URLs are allowed.",
        )
    return url


def _validate_enabled(enabled: Any) -> bool:
    if enabled is None:
        return True
    if not isinstance(enabled, bool):
        raise _source_error("MBOT-SOURCE-010", "Invalid source enabled value. Use true or false.")
    return enabled


def _parse_source(raw_source: Any, seen_names: set[str]) -> SourceDefinition:
    if not isinstance(raw_source, dict):
        raise _source_error("MBOT-SOURCE-009", "Each source entry must be a TOML table.")

    missing = [field for field in ("name", "kind", "url") if field not in raw_source]
    if missing:
        raise _source_error(
            "MBOT-SOURCE-002",
            f"Missing required source field: {', '.join(missing)}",
        )

    name = _validate_source_name(raw_source["name"])
    if name in seen_names:
        raise _source_error("MBOT-SOURCE-011", f"Duplicate source name: {name}")
    seen_names.add(name)

    return SourceDefinition(
        name=name,
        kind=_validate_source_kind(raw_source["kind"]),
        url=_validate_source_url(raw_source["url"]),
        enabled=_validate_enabled(raw_source.get("enabled")),
    )


def load_source_config(
    path: Path | None = None,
    project_name: str = DEFAULT_SOURCE_PROJECT_NAME,
) -> SourceConfig:
    """Load and validate source monitor config for a source project."""
    safe_project = validate_source_project_name(project_name)
    config_path = path if path is not None else source_config_path(safe_project)

    if not config_path.exists():
        return SourceConfig(
            path=config_path,
            exists=False,
            sources=(),
            project_name=safe_project,
        )

    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise _source_error("MBOT-SOURCE-006", f"Invalid source config TOML: {exc}") from exc
    except OSError as exc:
        raise _source_error("MBOT-SOURCE-007", f"Unable to read source config: {exc}") from exc

    if not isinstance(raw, dict):
        raise _source_error("MBOT-SOURCE-008", "Source config root must be a TOML table.")

    raw_sources = raw.get("sources", [])
    if not isinstance(raw_sources, list):
        raise _source_error("MBOT-SOURCE-001", "sources must be a TOML array of tables.")

    seen_names: set[str] = set()
    sources = tuple(_parse_source(source, seen_names) for source in raw_sources)

    return SourceConfig(
        path=config_path,
        exists=True,
        sources=sources,
        project_name=safe_project,
    )


def format_source_config_summary(config: SourceConfig) -> str:
    """Format a compact source config summary for operators."""
    lines = [
        "MarcBot source monitor config",
        f"Project: {config.project_name}",
        f"Path: {config.path}",
        f"Exists: {str(config.exists).lower()}",
        f"Sources: {len(config.sources)}",
        "",
    ]

    if not config.sources:
        lines.append("No sources configured.")
        return "\n".join(lines)

    for source in config.sources:
        state = "enabled" if source.enabled else "disabled"
        lines.extend(
            [
                f"- {source.name} [{source.kind}, {state}]",
                f"  {source.url}",
            ]
        )

    return "\n".join(lines)
