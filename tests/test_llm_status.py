"""Tests for read-only LLM status formatting."""

from pathlib import Path

import pytest

from marcbot.errors import MarcBotError
from marcbot.llm_status import format_llm_status_message, load_llm_env


def write_config(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "[providers.lmstudio]",
                "enabled = true",
                "type = \"openai_compatible\"",
                "base_url = \"http://192.0.2.10:1234/v1\"",
                "api_key_env = \"MARCBOT_LMSTUDIO_API_KEY\"",
                "",
                "[profiles.local_fast]",
                "provider = \"lmstudio\"",
                "model = \"google/gemma-4-e4b\"",
                "temperature = 0.2",
                "max_tokens = 500",
                "intended_use = \"low_risk_utility\"",
                "",
                "[profiles.local_careful]",
                "provider = \"lmstudio\"",
                "model = \"qwen3.6-35b-a3b\"",
                "temperature = 0.1",
                "max_tokens = 1200",
                "intended_use = \"bounded_local_analysis\"",
            ]
        ),
        encoding="utf-8",
    )


def test_load_llm_env_reads_key_values(tmp_path: Path) -> None:
    env_path = tmp_path / "llm.env"
    env_path.write_text(
        "\n".join(
            [
                "# comment",
                "MARCBOT_LMSTUDIO_API_KEY=secret-token",
                "OTHER_VALUE=\"quoted\"",
            ]
        ),
        encoding="utf-8",
    )

    values = load_llm_env(env_path)

    assert values == {
        "MARCBOT_LMSTUDIO_API_KEY": "secret-token",
        "OTHER_VALUE": "quoted",
    }


def test_load_llm_env_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(MarcBotError) as excinfo:
        load_llm_env(tmp_path / "missing.env")

    assert excinfo.value.code == "MBOT-LLM-038"


def test_load_llm_env_rejects_invalid_line(tmp_path: Path) -> None:
    env_path = tmp_path / "llm.env"
    env_path.write_text("not-a-key-value", encoding="utf-8")

    with pytest.raises(MarcBotError) as excinfo:
        load_llm_env(env_path)

    assert excinfo.value.code == "MBOT-LLM-039"


def test_format_llm_status_message_is_read_only(tmp_path: Path) -> None:
    config_path = tmp_path / "llm-providers.toml"
    write_config(config_path)

    message = format_llm_status_message(config_path=config_path)

    assert "🤖 MarcBot LLM status" in message
    assert "Profiles: 2" in message
    assert "- local_fast: google/gemma-4-e4b via lmstudio" in message
    assert "Provider contact: not performed" in message
    assert "Health checks: CLI-only via python -m marcbot llm health <profile>" in message
    assert "Health check:" not in message
    assert "Response: marcbot-ok" not in message
