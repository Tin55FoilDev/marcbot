"""Tests for MarcBot LLM provider/profile config."""

from pathlib import Path

import pytest

from marcbot.errors import MarcBotError
from marcbot.llm_config import format_llm_profile_detail, format_llm_profiles, load_llm_config


def write_llm_config(tmp_path: Path, content: str) -> Path:
    """Write a test LLM config file."""
    path = tmp_path / "llm-providers.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_llm_config_with_lmstudio_profile(tmp_path: Path) -> None:
    path = write_llm_config(
        tmp_path,
        """
[providers.lmstudio]
enabled = true
type = "openai_compatible"
base_url = "http://192.0.2.10:1234/v1"
api_key_env = "MARCBOT_LMSTUDIO_API_KEY"
timeout_seconds = 30

[profiles.local_fast]
provider = "lmstudio"
model = "google/gemma-4-e4b"
temperature = 0.2
max_tokens = 500
intended_use = "low_risk_utility"
chat_enabled = true
""",
    )

    config = load_llm_config(path)

    assert config.path == path
    assert config.providers["lmstudio"].base_url == "http://192.0.2.10:1234/v1"
    assert config.providers["lmstudio"].provider_type == "openai_compatible"
    assert config.profiles["local_fast"].provider == "lmstudio"
    assert config.profiles["local_fast"].model == "google/gemma-4-e4b"
    assert config.profiles["local_fast"].chat_enabled is True


def test_format_llm_profile_detail(tmp_path: Path) -> None:
    """Format one configured profile with provider details."""
    config_path = write_llm_config(
        tmp_path,
        """
[providers.lmstudio]
enabled = true
type = "openai_compatible"
base_url = "http://192.0.2.10:1234/v1"
api_key_env = "MARCBOT_LMSTUDIO_API_KEY"
timeout_seconds = 30

[profiles.local_fast]
provider = "lmstudio"
model = "google/gemma-4-e4b"
temperature = 0.2
max_tokens = 500
intended_use = "low_risk_utility"
""",
    )

    config = load_llm_config(config_path)
    profile = config.profiles["local_fast"]
    provider = config.providers[profile.provider]

    output = format_llm_profile_detail(profile, provider)

    assert "MarcBot LLM profile" in output
    assert "Name: local_fast" in output
    assert "Provider: lmstudio" in output
    assert "Provider type: openai_compatible" in output
    assert "Model: google/gemma-4-e4b" in output
    assert "Temperature: 0.2" in output
    assert "Max tokens: 500" in output
    assert "Intended use: low_risk_utility" in output
    assert "Chat enabled: no" in output
    assert "Provider enabled: yes" in output
    assert "Base URL: http://192.0.2.10:1234/v1" in output
    assert "API key env: MARCBOT_LMSTUDIO_API_KEY" in output


def test_format_llm_profiles(tmp_path: Path) -> None:
    path = write_llm_config(
        tmp_path,
        """
[providers.lmstudio]
type = "openai_compatible"
base_url = "http://192.0.2.10:1234/v1"

[profiles.local_fast]
provider = "lmstudio"
model = "google/gemma-4-e4b"
""",
    )

    output = format_llm_profiles(load_llm_config(path))

    assert "MarcBot LLM profiles" in output
    assert "- local_fast" in output
    assert "provider: lmstudio (openai_compatible, enabled)" in output
    assert "model: google/gemma-4-e4b" in output
    assert "chat_enabled: False" in output


def test_missing_llm_config_raises_clean_error(tmp_path: Path) -> None:
    with pytest.raises(MarcBotError) as excinfo:
        load_llm_config(tmp_path / "missing.toml")

    assert excinfo.value.code == "MBOT-LLM-001"


def test_openai_compatible_provider_requires_base_url(tmp_path: Path) -> None:
    path = write_llm_config(
        tmp_path,
        """
[providers.lmstudio]
type = "openai_compatible"

[profiles.local_fast]
provider = "lmstudio"
model = "google/gemma-4-e4b"
""",
    )

    with pytest.raises(MarcBotError) as excinfo:
        load_llm_config(path)

    assert excinfo.value.code == "MBOT-LLM-013"


def test_profile_must_reference_known_provider(tmp_path: Path) -> None:
    path = write_llm_config(
        tmp_path,
        """
[providers.lmstudio]
type = "openai_compatible"
base_url = "http://192.0.2.10:1234/v1"

[profiles.local_fast]
provider = "missing"
model = "google/gemma-4-e4b"
""",
    )

    with pytest.raises(MarcBotError) as excinfo:
        load_llm_config(path)

    assert excinfo.value.code == "MBOT-LLM-015"


def test_unknown_provider_type_raises_clean_error(tmp_path: Path) -> None:
    path = write_llm_config(
        tmp_path,
        """
[providers.lmstudio]
type = "bad"
base_url = "http://192.0.2.10:1234/v1"

[profiles.local_fast]
provider = "lmstudio"
model = "google/gemma-4-e4b"
""",
    )

    with pytest.raises(MarcBotError) as excinfo:
        load_llm_config(path)

    assert excinfo.value.code == "MBOT-LLM-012"

def test_profile_chat_enabled_must_be_bool(tmp_path: Path) -> None:
    path = write_llm_config(
        tmp_path,
        """
[providers.lmstudio]
type = "openai_compatible"
base_url = "http://192.0.2.10:1234/v1"

[profiles.local_fast]
provider = "lmstudio"
model = "google/gemma-4-e4b"
chat_enabled = "yes"
""",
    )

    with pytest.raises(MarcBotError) as excinfo:
        load_llm_config(path)

    assert excinfo.value.code == "MBOT-LLM-009"
    assert "profiles.local_fast.chat_enabled" in excinfo.value.message

def test_format_llm_profile_detail_reports_chat_enabled_yes(tmp_path: Path) -> None:
    config_path = write_llm_config(
        tmp_path,
        """
[providers.lmstudio]
enabled = true
type = "openai_compatible"
base_url = "http://192.0.2.10:1234/v1"
api_key_env = "MARCBOT_LMSTUDIO_API_KEY"
timeout_seconds = 30

[profiles.local_fast]
provider = "lmstudio"
model = "google/gemma-4-e4b"
temperature = 0.2
max_tokens = 500
intended_use = "low_risk_utility"
chat_enabled = true
""",
    )

    config = load_llm_config(config_path)
    profile = config.profiles["local_fast"]
    provider = config.providers[profile.provider]

    output = format_llm_profile_detail(profile, provider)

    assert "Chat enabled: yes" in output
