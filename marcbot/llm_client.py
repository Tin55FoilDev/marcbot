"""Small HTTP client for MarcBot LLM providers."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from marcbot.errors import MarcBotError
from marcbot.llm_config import LlmProviderConfig

MAX_LLM_PROMPT_CHARS = 4000


class UrlOpener(Protocol):
    """Protocol for urllib-compatible openers used by tests."""

    def open(
        self,
        request: urllib.request.Request,
        timeout: int,
    ) -> Any:
        """Open a URL request."""


@dataclass(frozen=True)
class LlmModelInfo:
    """One model returned by an LLM provider."""

    model_id: str
    owned_by: str = ""


@dataclass(frozen=True)
class LlmHealthResult:
    """Result from an LLM profile health check."""

    provider_name: str
    profile_name: str
    model: str
    response_text: str


@dataclass(frozen=True)
class LlmCompletionResult:
    """Result from a one-shot LLM profile completion."""

    provider_name: str
    profile_name: str
    model: str
    response_text: str
    finish_reason: str


def _provider_headers(provider: LlmProviderConfig) -> dict[str, str]:
    """Build HTTP headers for a provider."""
    headers = {
        "Accept": "application/json",
    }

    if provider.api_key_env:
        api_key = os.environ.get(provider.api_key_env, "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

    return headers


def _read_json_response(response: Any) -> dict[str, Any]:
    """Read and decode a JSON HTTP response."""
    try:
        raw_data = response.read()
    except OSError as exc:
        raise MarcBotError("MBOT-LLM-024", "Unable to read LLM provider response") from exc

    try:
        parsed = json.loads(raw_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MarcBotError("MBOT-LLM-025", "LLM provider returned invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise MarcBotError("MBOT-LLM-026", "LLM provider JSON response must be an object")

    return parsed


def _post_json_response(
    provider: LlmProviderConfig,
    endpoint: str,
    payload: dict[str, Any],
    opener: UrlOpener | None = None,
) -> dict[str, Any]:
    """POST JSON to an LLM provider endpoint and return parsed JSON."""
    if not provider.enabled:
        raise MarcBotError("MBOT-LLM-020", f"LLM provider is disabled: {provider.name}")

    if provider.provider_type != "openai_compatible":
        raise MarcBotError(
            "MBOT-LLM-021",
            f"LLM provider does not support this operation yet: {provider.name}",
        )

    if not provider.base_url:
        raise MarcBotError("MBOT-LLM-022", f"LLM provider is missing base_url: {provider.name}")

    headers = _provider_headers(provider)
    headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{provider.base_url}/{endpoint.lstrip('/')}",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    active_opener = opener or urllib.request.build_opener()

    try:
        with active_opener.open(request, timeout=provider.timeout_seconds) as response:
            return _read_json_response(response)
    except TimeoutError as exc:
        raise MarcBotError("MBOT-LLM-023", f"LLM provider timed out: {provider.name}") from exc
    except urllib.error.HTTPError as exc:
        message = f"LLM provider returned HTTP {exc.code}: {provider.name}"
        if exc.code in (401, 403) and provider.api_key_env:
            message += f". Check {provider.api_key_env}."
        raise MarcBotError("MBOT-LLM-027", message) from exc
    except urllib.error.URLError as exc:
        raise MarcBotError(
            "MBOT-LLM-028",
            f"Unable to reach LLM provider: {provider.name}",
        ) from exc
    except OSError as exc:
        raise MarcBotError("MBOT-LLM-029", f"LLM provider request failed: {provider.name}") from exc


def list_openai_compatible_models(
    provider: LlmProviderConfig,
    opener: UrlOpener | None = None,
) -> tuple[LlmModelInfo, ...]:
    """List models from an OpenAI-compatible provider."""
    if not provider.enabled:
        raise MarcBotError("MBOT-LLM-020", f"LLM provider is disabled: {provider.name}")

    if provider.provider_type != "openai_compatible":
        raise MarcBotError(
            "MBOT-LLM-021",
            f"LLM provider does not support model discovery yet: {provider.name}",
        )

    if not provider.base_url:
        raise MarcBotError("MBOT-LLM-022", f"LLM provider is missing base_url: {provider.name}")

    request = urllib.request.Request(
        f"{provider.base_url}/models",
        headers=_provider_headers(provider),
        method="GET",
    )
    active_opener = opener or urllib.request.build_opener()

    try:
        with active_opener.open(request, timeout=provider.timeout_seconds) as response:
            parsed = _read_json_response(response)
    except TimeoutError as exc:
        raise MarcBotError("MBOT-LLM-023", f"LLM provider timed out: {provider.name}") from exc
    except urllib.error.HTTPError as exc:
        message = f"LLM provider returned HTTP {exc.code}: {provider.name}"
        if exc.code in (401, 403) and provider.api_key_env:
            message += f". Check {provider.api_key_env}."
        raise MarcBotError("MBOT-LLM-027", message) from exc
    except urllib.error.URLError as exc:
        raise MarcBotError(
            "MBOT-LLM-028",
            f"Unable to reach LLM provider: {provider.name}",
        ) from exc
    except OSError as exc:
        raise MarcBotError("MBOT-LLM-029", f"LLM provider request failed: {provider.name}") from exc

    raw_models = parsed.get("data")
    if not isinstance(raw_models, list):
        raise MarcBotError("MBOT-LLM-030", "LLM provider model list must contain data array")

    models: list[LlmModelInfo] = []
    for item in raw_models:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if not isinstance(model_id, str) or not model_id.strip():
            continue
        owned_by = item.get("owned_by", "")
        models.append(
            LlmModelInfo(
                model_id=model_id.strip(),
                owned_by=owned_by.strip() if isinstance(owned_by, str) else "",
            )
        )

    return tuple(sorted(models, key=lambda model: model.model_id))


def _first_chat_completion_text(parsed: dict[str, Any], purpose: str) -> tuple[str, str]:
    """Extract the first chat completion message text and finish reason."""
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        raise MarcBotError("MBOT-LLM-032", f"LLM {purpose} response has no choices")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise MarcBotError("MBOT-LLM-033", f"LLM {purpose} choice must be an object")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise MarcBotError("MBOT-LLM-034", f"LLM {purpose} choice has no message object")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise MarcBotError("MBOT-LLM-035", f"LLM {purpose} response content is empty")

    finish_reason = first_choice.get("finish_reason")
    if not isinstance(finish_reason, str) or not finish_reason.strip():
        finish_reason = "unknown"

    return content.strip(), finish_reason.strip()


def run_openai_compatible_completion(
    provider: LlmProviderConfig,
    profile_name: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    opener: UrlOpener | None = None,
) -> LlmCompletionResult:
    """Run a bounded one-shot chat completion for a configured profile."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise MarcBotError("MBOT-LLM-038", "LLM completion prompt must not be empty")

    if len(prompt.strip()) > MAX_LLM_PROMPT_CHARS:
        raise MarcBotError(
            "MBOT-LLM-040",
            f"LLM completion prompt exceeds {MAX_LLM_PROMPT_CHARS} characters",
        )

    if max_tokens < 1:
        raise MarcBotError("MBOT-LLM-039", "LLM completion max_tokens must be positive")

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt.strip(),
            },
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    parsed = _post_json_response(
        provider=provider,
        endpoint="chat/completions",
        payload=payload,
        opener=opener,
    )

    response_text, finish_reason = _first_chat_completion_text(parsed, "completion")

    return LlmCompletionResult(
        provider_name=provider.name,
        profile_name=profile_name,
        model=model,
        response_text=response_text,
        finish_reason=finish_reason,
    )


def run_openai_compatible_health_check(
    provider: LlmProviderConfig,
    profile_name: str,
    model: str,
    opener: UrlOpener | None = None,
) -> LlmHealthResult:
    """Run a tiny deterministic chat completion health check."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "Reply exactly: marcbot-ok",
            },
        ],
        "temperature": 0,
        "max_tokens": 80,
    }

    parsed = _post_json_response(
        provider=provider,
        endpoint="chat/completions",
        payload=payload,
        opener=opener,
    )

    response_text, _finish_reason = _first_chat_completion_text(parsed, "health")
    if "marcbot-ok" not in response_text.lower():
        raise MarcBotError(
            "MBOT-LLM-036",
            f"LLM health response did not contain expected marker: {profile_name}",
        )

    return LlmHealthResult(
        provider_name=provider.name,
        profile_name=profile_name,
        model=model,
        response_text=response_text,
    )


def format_llm_completion_result(result: LlmCompletionResult) -> str:
    """Format a one-shot LLM completion result for operator output."""
    return "\n".join(
        [
            "MarcBot LLM completion",
            f"Profile: {result.profile_name}",
            f"Provider: {result.provider_name}",
            f"Model: {result.model}",
            f"Finish reason: {result.finish_reason}",
            "",
            result.response_text,
        ]
    )


def format_llm_health_result(result: LlmHealthResult) -> str:
    """Format an LLM health check result for operator output."""
    return "\n".join(
        [
            "MarcBot LLM health",
            f"Profile: {result.profile_name}",
            f"Provider: {result.provider_name}",
            f"Model: {result.model}",
            "Status: ok",
            f"Response: {result.response_text}",
        ]
    )


def format_llm_models(provider_name: str, models: tuple[LlmModelInfo, ...]) -> str:
    """Format LLM provider models for operator output."""
    lines = [
        "MarcBot LLM models",
        f"Provider: {provider_name}",
        f"Count: {len(models)}",
        "",
    ]

    if not models:
        lines.append("No models returned.")
        return "\n".join(lines)

    for model in models:
        if model.owned_by:
            lines.append(f"- {model.model_id} ({model.owned_by})")
        else:
            lines.append(f"- {model.model_id}")

    return "\n".join(lines)
