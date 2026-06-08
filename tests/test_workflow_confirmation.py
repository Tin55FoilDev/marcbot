from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from marcbot.workflow_confirmation import WorkflowConfirmationStore


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 6, 7, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, *, seconds: int) -> None:
        self.value = self.value + timedelta(seconds=seconds)


def test_issue_creates_provider_contact_confirmation_token() -> None:
    clock = Clock()
    store = WorkflowConfirmationStore(
        now_fn=clock,
        token_factory=lambda: "token-1",
    )

    record = store.issue(
        workflow_id="source-monitor-ai-summary",
        chat_id=123,
        ttl_seconds=60,
    )

    assert record.token == "token-1"
    assert record.workflow_id == "source-monitor-ai-summary"
    assert record.chat_id == 123
    assert record.issued_at == clock.value
    assert record.expires_at == clock.value + timedelta(seconds=60)
    assert record.used_at is None


def test_issue_rejects_unsupported_workflow() -> None:
    store = WorkflowConfirmationStore(token_factory=lambda: "token-1")

    with pytest.raises(ValueError, match="unsupported provider-contact workflow"):
        store.issue(workflow_id="source-monitor-ai-report", chat_id=123)


def test_consume_accepts_matching_token_once() -> None:
    clock = Clock()
    store = WorkflowConfirmationStore(
        now_fn=clock,
        token_factory=lambda: "token-1",
    )
    store.issue(
        workflow_id="source-monitor-ai-summary",
        chat_id=123,
        ttl_seconds=60,
    )

    result = store.consume(
        workflow_id="source-monitor-ai-summary",
        chat_id=123,
        token="token-1",
    )

    assert result.ok is True
    assert result.reason == "accepted"
    assert result.record is not None
    assert result.record.used_at == clock.value

    second_result = store.consume(
        workflow_id="source-monitor-ai-summary",
        chat_id=123,
        token="token-1",
    )

    assert second_result.ok is False
    assert second_result.reason == "already_used"


def test_consume_rejects_missing_and_unknown_tokens() -> None:
    store = WorkflowConfirmationStore(token_factory=lambda: "token-1")

    missing = store.consume(
        workflow_id="source-monitor-ai-summary",
        chat_id=123,
        token=" ",
    )
    unknown = store.consume(
        workflow_id="source-monitor-ai-summary",
        chat_id=123,
        token="not-known",
    )

    assert missing.ok is False
    assert missing.reason == "missing_token"
    assert unknown.ok is False
    assert unknown.reason == "unknown_token"


def test_consume_rejects_workflow_and_chat_mismatch() -> None:
    store = WorkflowConfirmationStore(token_factory=lambda: "token-1")
    store.issue(
        workflow_id="source-monitor-ai-summary",
        chat_id=123,
        ttl_seconds=60,
    )

    workflow_result = store.consume(
        workflow_id="source-monitor-ai-report",
        chat_id=123,
        token="token-1",
    )
    chat_result = store.consume(
        workflow_id="source-monitor-ai-summary",
        chat_id=456,
        token="token-1",
    )

    assert workflow_result.ok is False
    assert workflow_result.reason == "unsupported_workflow"
    assert chat_result.ok is False
    assert chat_result.reason == "chat_mismatch"


def test_consume_rejects_expired_token() -> None:
    clock = Clock()
    store = WorkflowConfirmationStore(
        now_fn=clock,
        token_factory=lambda: "token-1",
    )
    store.issue(
        workflow_id="source-monitor-ai-summary",
        chat_id=123,
        ttl_seconds=60,
    )

    clock.advance(seconds=61)

    result = store.consume(
        workflow_id="source-monitor-ai-summary",
        chat_id=123,
        token="token-1",
    )

    assert result.ok is False
    assert result.reason == "expired"
