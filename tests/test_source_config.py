from pathlib import Path

import pytest

from marcbot.errors import MarcBotError
from marcbot.source_config import (
    DEFAULT_SOURCE_PROJECT_NAME,
    SourceConfig,
    format_source_config_summary,
    load_source_config,
    source_config_path,
    source_reports_dir,
    validate_source_project_name,
)


def test_source_config_path_uses_project_layout() -> None:
    assert source_config_path("ai") == Path(
        "/srv/marcbot/config/source-projects/ai/sources.toml"
    )


def test_source_reports_dir_uses_project_layout() -> None:
    assert source_reports_dir("ai") == Path(
        "/srv/marcbot/workspace/source-projects/ai/reports"
    )



def test_load_source_config_accepts_rss_feed_kind(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.toml"
    config_path.write_text(
        """
[[sources]]
name = "openai-news"
kind = "rss_feed"
url = "https://openai.com/news/rss.xml"
enabled = true
""",
        encoding="utf-8",
    )

    config = load_source_config(path=config_path)

    assert config.sources[0].kind == "rss_feed"

@pytest.mark.parametrize(
    "project_name",
    ["ai", "stocks", "openclaw-updates", "project_1"],
)
def test_validate_source_project_name_accepts_safe_slugs(project_name: str) -> None:
    assert validate_source_project_name(project_name) == project_name


@pytest.mark.parametrize(
    "project_name",
    ["", "../ai", "AI", "ai/news", "bad project", ".hidden"],
)
def test_validate_source_project_name_rejects_unsafe_names(project_name: str) -> None:
    with pytest.raises(MarcBotError, match="Invalid source project name"):
        validate_source_project_name(project_name)


def test_missing_source_config_returns_empty_config(tmp_path: Path) -> None:
    config_path = tmp_path / "missing.toml"

    config = load_source_config(path=config_path, project_name="ai")

    assert config == SourceConfig(
        path=config_path,
        exists=False,
        sources=(),
        project_name="ai",
    )


def test_valid_source_config_loads_sources(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.toml"
    config_path.write_text(
        """
[[sources]]
name = "openai-news"
kind = "web_page"
url = "https://openai.com/news/"
enabled = true

[[sources]]
name = "disabled-source"
kind = "github_releases"
url = "https://github.com/example/project/releases"
enabled = false
""",
        encoding="utf-8",
    )

    config = load_source_config(path=config_path, project_name="ai")

    assert config.project_name == "ai"
    assert config.path == config_path
    assert config.exists is True
    assert len(config.sources) == 2
    assert config.sources[0].name == "openai-news"
    assert config.sources[0].kind == "web_page"
    assert config.sources[0].url == "https://openai.com/news/"
    assert config.sources[0].enabled is True
    assert config.sources[1].enabled is False


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            """
[[sources]]
name = "Bad Name"
kind = "web_page"
url = "https://example.com"
""",
            "Invalid source name",
        ),
        (
            """
[[sources]]
name = "bad-kind"
kind = "rss"
url = "https://example.com"
""",
            "Invalid source kind",
        ),
        (
            """
[[sources]]
name = "bad-url"
kind = "web_page"
url = "http://example.com"
""",
            "Invalid source URL",
        ),
        (
            """
[[sources]]
name = "bad-enabled"
kind = "web_page"
url = "https://example.com"
enabled = "yes"
""",
            "Invalid source enabled",
        ),
        (
            """
[[sources]]
name = "duplicate"
kind = "web_page"
url = "https://example.com/a"

[[sources]]
name = "duplicate"
kind = "web_page"
url = "https://example.com/b"
""",
            "Duplicate source name",
        ),
    ],
)

def test_invalid_source_config_raises_clean_error(
    tmp_path: Path,
    body: str,
    expected: str,
) -> None:
    config_path = tmp_path / "sources.toml"
    config_path.write_text(body, encoding="utf-8")

    with pytest.raises(MarcBotError, match=expected):
        load_source_config(path=config_path, project_name="ai")


def test_format_source_config_summary_for_missing_config(tmp_path: Path) -> None:
    config = SourceConfig(
        path=tmp_path / "missing.toml",
        exists=False,
        sources=(),
        project_name=DEFAULT_SOURCE_PROJECT_NAME,
    )

    summary = format_source_config_summary(config)

    assert "MarcBot source monitor config" in summary
    assert "Project: ai" in summary
    assert "Exists: false" in summary
    assert "Sources: 0" in summary
    assert "No sources configured." in summary


def test_format_source_config_summary_lists_sources(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.toml"
    config_path.write_text(
        """
[[sources]]
name = "openai-news"
kind = "web_page"
url = "https://openai.com/news/"
enabled = true
""",
        encoding="utf-8",
    )

    config = load_source_config(path=config_path, project_name="ai")
    summary = format_source_config_summary(config)

    assert "Project: ai" in summary
    assert "- openai-news [web_page, enabled]" in summary
    assert "https://openai.com/news/" in summary
