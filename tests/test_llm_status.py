"""Tests for read-only LLM status formatting."""

from pathlib import Path

import pytest

from marcbot.errors import MarcBotError
from marcbot.llm_client import LlmHealthResult
from marcbot.llm_status import format_llm_status_message, load_llm_env


def write_config(path: Path) -> None:
    path.write_text(
        """
[providers.lmstudio]
enabled = true
type = "openai_compatible"
base_url = "http://192.0.2.10:1234/v1"
api_key_env = "MARCBOT_LMSTUDIO_API_KEY"

[profiles.local_fast]
provider = "lmstudio"
model = "google/gemma-4-e4b"
temperature = 0.2
max_tokens = 500
intended_use = "low_risk_utility"

[profiles.local_careful]
provider = "lmstudio"
model = "qwen3.6-35b-a3b"
temperature = 0.1
max_tokens = 1200
intended_use = "bounded_local_analysis"
""".strip(),
        encoding="utf-8",
    )


def test_load_llm_env_reads_key_values(tmp_path: Path) -> None:
    env_path = tmp_path / "llm.env"
    env_path.write_text(
        """
# comment
MARCBOT_LMSTUDIO_API_KEY=secret-token
OTHER_VALUE="quoted"
""".strip(),
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


def test_format_llm_status_message_runs_local_fast_health(tmp_path: Path) -> None:
    config_path = tmp_path / "llm-providers.toml"
    env_path = tmp_path / "llm.env"
    write_config(config_path)
    env_path.write_text("MARCBOT_LMSTUDIO_API_KEY=test-token\n", encoding="utf-8")

    calls: list[tuple[str, str, str]] = []

    def fake_health_runner(*, provider, profile_name, model):
        calls.append((provider.name, profile_name, model))
        return LlmHealthResult(
            provider_name=provider.name,
            profile_name=profile_name,
            model=model,
            response_text="marcbot-ok",
        )

    message = format_llm_status_message(
        config_path=config_path,
        env_path=env_path,
        health_runner=fake_health_runner,
    )

    assert "🤖 MarcBot LLM status" in message
    assert "Profiles: 2" in message
    assert "- local_fast: google/gemma-4-e4b via lmstudio" in message
    assert "Health check:" in message
    assert "Profile: local_fast" in message
    assert "Status: ok" in message
    assert "Response: marcbot-ok" in message
    assert "test-token" not in message
    assert calls == [("lmstudio", "local_fast", "google/gemma-4-e4b")]


def test_format_llm_status_message_reports_health_error(tmp_path: Path) -> None:
    config_path = tmp_path / "llm-providers.toml"
    env_path = tmp_path / "llm.env"
    write_config(config_path)
    env_path.write_text("MARCBOT_LMSTUDIO_API_KEY=test-token\n", encoding="utf-8")

    def fake_health_runner(*, provider, profile_name, model):
        raise MarcBotError("MBOT-TEST-001", "simulated health failure")

    message = format_llm_status_message(
        config_path=config_path,
        env_path=env_path,
        health_runner=fake_health_runner,
    )

    assert "Status: error" in message
    assert "Error: [MBOT-TEST-001] simulated health failure" in message
    assert "test-token" not in message
