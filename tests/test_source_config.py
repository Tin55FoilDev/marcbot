"""Tests for MarcBot source monitor config validation."""

from pathlib import Path

import pytest

from marcbot.errors import MarcBotError
from marcbot.source_config import (
    SourceDefinition,
    format_source_config_summary,
    load_source_config,
)


def test_missing_source_config_returns_empty_config(tmp_path: Path) -> None:
    path = tmp_path / "missing-sources.toml"

    config = load_source_config(path)

    assert config.path == path
    assert config.exists is False
    assert config.sources == ()


def test_valid_source_config_loads_sources(tmp_path: Path) -> None:
    path = tmp_path / "sources.toml"
    path.write_text(
        """
[[sources]]
name = "openclaw_releases"
kind = "github_releases"
url = "https://github.com/example/openclaw/releases"
enabled = true

[[sources]]
name = "vllm-releases"
kind = "github_releases"
url = "https://github.com/vllm-project/vllm/releases"
enabled = false
""",
        encoding="utf-8",
    )

    config = load_source_config(path)

    assert config.exists is True
    assert config.sources == (
        SourceDefinition(
            name="openclaw_releases",
            kind="github_releases",
            url="https://github.com/example/openclaw/releases",
            enabled=True,
        ),
        SourceDefinition(
            name="vllm-releases",
            kind="github_releases",
            url="https://github.com/vllm-project/vllm/releases",
            enabled=False,
        ),
    )


@pytest.mark.parametrize(
    ("toml_text", "error_code"),
    [
        (
            """
[[sources]]
name = "Bad Name"
kind = "github_releases"
url = "https://example.com"
""",
            "MBOT-SOURCE-003",
        ),
        (
            """
[[sources]]
name = "bad_kind"
kind = "rss"
url = "https://example.com"
""",
            "MBOT-SOURCE-004",
        ),
        (
            """
[[sources]]
name = "bad_url"
kind = "web_page"
url = "http://example.com"
""",
            "MBOT-SOURCE-005",
        ),
        (
            """
[[sources]]
name = "duplicate"
kind = "web_page"
url = "https://example.com/one"

[[sources]]
name = "duplicate"
kind = "web_page"
url = "https://example.com/two"
""",
            "MBOT-SOURCE-011",
        ),
    ],
)
def test_invalid_source_config_raises_clean_error(
    tmp_path: Path,
    toml_text: str,
    error_code: str,
) -> None:
    path = tmp_path / "sources.toml"
    path.write_text(toml_text, encoding="utf-8")

    with pytest.raises(MarcBotError) as exc_info:
        load_source_config(path)

    assert exc_info.value.code == error_code


def test_format_source_config_summary_for_missing_config(tmp_path: Path) -> None:
    config = load_source_config(tmp_path / "missing.toml")

    summary = format_source_config_summary(config)

    assert "MarcBot source monitor config" in summary
    assert "Exists: false" in summary
    assert "Sources: 0" in summary
    assert "No sources configured." in summary


def test_format_source_config_summary_lists_sources(tmp_path: Path) -> None:
    path = tmp_path / "sources.toml"
    path.write_text(
        """
[[sources]]
name = "example"
kind = "web_page"
url = "https://example.com"
""",
        encoding="utf-8",
    )

    summary = format_source_config_summary(load_source_config(path))

    assert "Exists: true" in summary
    assert "Sources: 1" in summary
    assert "- example [web_page, enabled]" in summary
    assert "https://example.com" in summary
