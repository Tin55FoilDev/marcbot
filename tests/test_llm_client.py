"""Tests for MarcBot LLM client behavior."""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass

import pytest

from marcbot.errors import MarcBotError
from marcbot.llm_client import (
    MAX_LLM_PROMPT_CHARS,
    format_llm_completion_result,
    format_llm_health_result,
    format_llm_models,
    list_openai_compatible_models,
    run_openai_compatible_completion,
    run_openai_compatible_health_check,
)
from marcbot.llm_config import LlmProviderConfig


@dataclass
class FakeResponse:
    """Minimal context-manager HTTP response for tests."""

    data: bytes

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self.data


class FakeOpener:
    """Minimal opener for tests."""

    def __init__(self, response: FakeResponse | Exception):
        self.response = response
        self.requests: list[urllib.request.Request] = []
        self.timeouts: list[int] = []

    def open(self, request: urllib.request.Request, timeout: int) -> FakeResponse:
        self.requests.append(request)
        self.timeouts.append(timeout)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def make_provider(**overrides) -> LlmProviderConfig:
    """Build a test provider."""
    values = {
        "name": "lmstudio",
        "enabled": True,
        "provider_type": "openai_compatible",
        "base_url": "http://192.0.2.10:1234/v1",
        "api_key_env": "",
        "timeout_seconds": 30,
    }
    values.update(overrides)
    return LlmProviderConfig(**values)


def test_list_openai_compatible_models() -> None:
    opener = FakeOpener(
        FakeResponse(
            b"""{
              "object": "list",
              "data": [
                {"id": "qwen3.6-35b-a3b", "owned_by": "lmstudio"},
                {"id": "google/gemma-4-e4b"}
              ]
            }"""
        )
    )

    models = list_openai_compatible_models(make_provider(), opener=opener)

    assert [model.model_id for model in models] == [
        "google/gemma-4-e4b",
        "qwen3.6-35b-a3b",
    ]
    assert opener.requests[0].full_url == "http://192.0.2.10:1234/v1/models"
    assert opener.timeouts == [30]


def test_list_models_adds_authorization_when_env_is_set(monkeypatch) -> None:
    monkeypatch.setenv("MARCBOT_LMSTUDIO_API_KEY", "test-token")
    opener = FakeOpener(FakeResponse(b"{\"data\": []}"))

    list_openai_compatible_models(
        make_provider(api_key_env="MARCBOT_LMSTUDIO_API_KEY"),
        opener=opener,
    )

    assert opener.requests[0].headers["Authorization"] == "Bearer test-token"


def test_list_models_omits_authorization_when_env_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("MARCBOT_LMSTUDIO_API_KEY", raising=False)
    opener = FakeOpener(FakeResponse(b"{\"data\": []}"))

    list_openai_compatible_models(
        make_provider(api_key_env="MARCBOT_LMSTUDIO_API_KEY"),
        opener=opener,
    )

    assert "Authorization" not in opener.requests[0].headers


def test_disabled_provider_raises_clean_error() -> None:
    with pytest.raises(MarcBotError) as excinfo:
        list_openai_compatible_models(
            make_provider(enabled=False),
            opener=FakeOpener(FakeResponse(b"{}")),
        )

    assert excinfo.value.code == "MBOT-LLM-020"


def test_non_openai_compatible_provider_raises_clean_error() -> None:
    with pytest.raises(MarcBotError) as excinfo:
        list_openai_compatible_models(
            make_provider(provider_type="openai"),
            opener=FakeOpener(FakeResponse(b"{}")),
        )

    assert excinfo.value.code == "MBOT-LLM-021"


def test_invalid_json_raises_clean_error() -> None:
    with pytest.raises(MarcBotError) as excinfo:
        list_openai_compatible_models(make_provider(), opener=FakeOpener(FakeResponse(b"not-json")))

    assert excinfo.value.code == "MBOT-LLM-025"


def test_missing_data_array_raises_clean_error() -> None:
    with pytest.raises(MarcBotError) as excinfo:
        list_openai_compatible_models(make_provider(), opener=FakeOpener(FakeResponse(b"{}")))

    assert excinfo.value.code == "MBOT-LLM-030"


def test_url_error_raises_clean_error() -> None:
    with pytest.raises(MarcBotError) as excinfo:
        list_openai_compatible_models(
            make_provider(),
            opener=FakeOpener(urllib.error.URLError("connection refused")),
        )

    assert excinfo.value.code == "MBOT-LLM-028"


def test_http_auth_error_mentions_api_key_env() -> None:
    request = urllib.request.Request("http://example.invalid/v1/models")
    error = urllib.error.HTTPError(
        url=request.full_url,
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=None,
    )

    with pytest.raises(MarcBotError) as excinfo:
        list_openai_compatible_models(
            make_provider(api_key_env="MARCBOT_LMSTUDIO_API_KEY"),
            opener=FakeOpener(error),
        )

    assert excinfo.value.code == "MBOT-LLM-027"
    assert "Check MARCBOT_LMSTUDIO_API_KEY" in str(excinfo.value)


def test_format_llm_models() -> None:
    models = list_openai_compatible_models(
        make_provider(),
        opener=FakeOpener(FakeResponse(b"{\"data\": [{\"id\": \"model-a\"}]}")),
    )

    output = format_llm_models("lmstudio", models)

    assert "MarcBot LLM models" in output
    assert "Provider: lmstudio" in output
    assert "Count: 1" in output
    assert "- model-a" in output

def test_run_openai_compatible_completion() -> None:
    opener = FakeOpener(
        FakeResponse(
            b"""{
              "choices": [
                {
                  "finish_reason": "stop",
                  "message": {
                    "content": "Hello from MarcBot"
                  }
                }
              ]
            }"""
        )
    )

    result = run_openai_compatible_completion(
        provider=make_provider(),
        profile_name="local_fast",
        model="google/gemma-4-e4b",
        prompt="Say hello.",
        temperature=0.2,
        max_tokens=100,
        opener=opener,
    )

    assert result.provider_name == "lmstudio"
    assert result.profile_name == "local_fast"
    assert result.model == "google/gemma-4-e4b"
    assert result.response_text == "Hello from MarcBot"
    assert result.finish_reason == "stop"
    assert opener.requests[0].full_url == "http://192.0.2.10:1234/v1/chat/completions"
    assert opener.requests[0].get_method() == "POST"


def test_run_openai_compatible_completion_rejects_empty_prompt() -> None:
    with pytest.raises(MarcBotError) as excinfo:
        run_openai_compatible_completion(
            provider=make_provider(),
            profile_name="local_fast",
            model="google/gemma-4-e4b",
            prompt="   ",
            temperature=0.2,
            max_tokens=100,
            opener=FakeOpener(FakeResponse(b"{\"choices\": []}")),
        )

    assert excinfo.value.code == "MBOT-LLM-038"


def test_run_openai_compatible_completion_rejects_overlong_prompt() -> None:
    with pytest.raises(MarcBotError) as excinfo:
        run_openai_compatible_completion(
            provider=make_provider(),
            profile_name="local_fast",
            model="google/gemma-4-e4b",
            prompt="x" * (MAX_LLM_PROMPT_CHARS + 1),
            temperature=0.2,
            max_tokens=100,
            opener=FakeOpener(FakeResponse(b"{\"choices\": []}")),
        )

    assert excinfo.value.code == "MBOT-LLM-040"


def test_run_openai_compatible_completion_rejects_nonpositive_max_tokens() -> None:
    with pytest.raises(MarcBotError) as excinfo:
        run_openai_compatible_completion(
            provider=make_provider(),
            profile_name="local_fast",
            model="google/gemma-4-e4b",
            prompt="Say hello.",
            temperature=0.2,
            max_tokens=0,
            opener=FakeOpener(FakeResponse(b"{\"choices\": []}")),
        )

    assert excinfo.value.code == "MBOT-LLM-039"


def test_format_llm_completion_result() -> None:
    result = run_openai_compatible_completion(
        provider=make_provider(),
        profile_name="local_fast",
        model="google/gemma-4-e4b",
        prompt="Say hello.",
        temperature=0.2,
        max_tokens=100,
        opener=FakeOpener(
            FakeResponse(
                b"""{
                  "choices": [
                    {
                      "finish_reason": "stop",
                      "message": {
                        "content": "Hello"
                      }
                    }
                  ]
                }"""
            )
        ),
    )

    output = format_llm_completion_result(result)

    assert "MarcBot LLM completion" in output
    assert "Profile: local_fast" in output
    assert "Provider: lmstudio" in output
    assert "Finish reason: stop" in output
    assert "Hello" in output


def test_run_openai_compatible_health_check() -> None:
    opener = FakeOpener(
        FakeResponse(
            b"""{
              "choices": [
                {
                  "message": {
                    "content": "marcbot-ok"
                  }
                }
              ]
            }"""
        )
    )

    result = run_openai_compatible_health_check(
        provider=make_provider(),
        profile_name="local_fast",
        model="google/gemma-4-e4b",
        opener=opener,
    )

    assert result.provider_name == "lmstudio"
    assert result.profile_name == "local_fast"
    assert result.model == "google/gemma-4-e4b"
    assert result.response_text == "marcbot-ok"
    assert opener.requests[0].full_url == "http://192.0.2.10:1234/v1/chat/completions"
    assert opener.requests[0].get_method() == "POST"


def test_run_health_check_requires_expected_marker() -> None:
    opener = FakeOpener(
        FakeResponse(
            b"""{
              "choices": [
                {
                  "message": {
                    "content": "wrong"
                  }
                }
              ]
            }"""
        )
    )

    with pytest.raises(MarcBotError) as excinfo:
        run_openai_compatible_health_check(
            provider=make_provider(),
            profile_name="local_fast",
            model="google/gemma-4-e4b",
            opener=opener,
        )

    assert excinfo.value.code == "MBOT-LLM-036"


def test_run_health_check_rejects_empty_choices() -> None:
    with pytest.raises(MarcBotError) as excinfo:
        run_openai_compatible_health_check(
            provider=make_provider(),
            profile_name="local_fast",
            model="google/gemma-4-e4b",
            opener=FakeOpener(FakeResponse(b"{\"choices\": []}")),
        )

    assert excinfo.value.code == "MBOT-LLM-032"


def test_format_llm_health_result() -> None:
    result = run_openai_compatible_health_check(
        provider=make_provider(),
        profile_name="local_fast",
        model="google/gemma-4-e4b",
        opener=FakeOpener(
            FakeResponse(b"{\"choices\": [{\"message\": {\"content\": \"marcbot-ok\"}}]}")
        ),
    )

    output = format_llm_health_result(result)

    assert "MarcBot LLM health check" in output
    assert "Profile: local_fast" in output
    assert "Provider: lmstudio" in output
    assert "Result: OK" in output
    assert "Response: marcbot-ok" in output
