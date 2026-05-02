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
