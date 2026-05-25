from marcbot.memory_candidate import (
    format_memory_candidate_preview,
    preview_memory_candidate,
)


def test_preview_memory_candidate_detects_high_risk_secret_text() -> None:
    preview = preview_memory_candidate(
        text="Remember this API key for later.",
        project="source-monitor",
    )

    assert preview.action == "manual_review"
    assert preview.risk_level == "high"
    assert preview.project == "source-monitor"
    assert preview.provider_contact is False
    assert preview.writes is False


def test_preview_memory_candidate_detects_durable_fact_candidate() -> None:
    preview = preview_memory_candidate(
        text="Source-monitor summaries should use explicit memory profiles.",
        project="source-monitor",
    )

    assert preview.action == "propose_fact"
    assert preview.risk_level == "medium"


def test_preview_memory_candidate_detects_event_candidate() -> None:
    preview = preview_memory_candidate(
        text="Source-monitor summary generated successfully.",
        project="source-monitor",
    )

    assert preview.action == "record_event"
    assert preview.risk_level == "low"


def test_preview_memory_candidate_ignores_low_signal_text() -> None:
    preview = preview_memory_candidate(text="hello there")

    assert preview.action == "ignore"
    assert preview.risk_level == "low"


def test_format_memory_candidate_preview_includes_boundaries() -> None:
    preview = preview_memory_candidate(
        text="Remember source-monitor preferences.",
        project="source-monitor",
    )

    message = format_memory_candidate_preview(preview)

    assert "MarcBot memory candidate preview" in message
    assert "Action: propose_fact" in message
    assert "Provider contact: no" in message
    assert "Writes: no" in message


def test_format_memory_candidate_preview_json_is_structured() -> None:
    import json

    from marcbot.memory_candidate import format_memory_candidate_preview_json

    preview = preview_memory_candidate(
        text="Source-monitor summaries should use explicit memory profiles.",
        project="source-monitor",
    )

    payload = json.loads(format_memory_candidate_preview_json(preview))

    assert payload == {
        "action": "propose_fact",
        "input_text": "Source-monitor summaries should use explicit memory profiles.",
        "project": "source-monitor",
        "provider_contact": False,
        "reason": "text looks like a durable instruction, preference, or policy",
        "risk_level": "medium",
        "writes": False,
    }


def test_preview_memory_candidate_proposal_for_fact_candidate() -> None:
    from marcbot.memory_candidate import preview_memory_candidate_proposal

    preview = preview_memory_candidate_proposal(
        text="Source-monitor summaries should use explicit memory profiles.",
        project="source-monitor",
    )

    assert preview.would_create_proposal is True
    assert preview.proposal_type == "fact"
    assert preview.risk_level == "medium"
    assert preview.project == "source-monitor"
    assert preview.proposed_statement == (
        "Source-monitor summaries should use explicit memory profiles."
    )
    assert preview.provider_contact is False
    assert preview.writes is False


def test_preview_memory_candidate_proposal_for_non_fact_candidate() -> None:
    from marcbot.memory_candidate import preview_memory_candidate_proposal

    preview = preview_memory_candidate_proposal(
        text="Source-monitor summary generated successfully.",
        project="source-monitor",
    )

    assert preview.would_create_proposal is False
    assert preview.proposal_type is None
    assert preview.risk_level == "low"
    assert preview.proposed_statement is None
    assert preview.provider_contact is False
    assert preview.writes is False


def test_format_memory_proposal_preview_json_is_structured() -> None:
    import json

    from marcbot.memory_candidate import (
        format_memory_proposal_preview_json,
        preview_memory_candidate_proposal,
    )

    preview = preview_memory_candidate_proposal(
        text="Source-monitor summaries should use explicit memory profiles.",
        project="source-monitor",
    )

    payload = json.loads(format_memory_proposal_preview_json(preview))

    assert payload["would_create_proposal"] is True
    assert payload["proposal_type"] == "fact"
    assert payload["risk_level"] == "medium"
    assert payload["project"] == "source-monitor"
    assert payload["provider_contact"] is False
    assert payload["writes"] is False


def test_format_memory_candidate_status_lists_boundaries() -> None:
    from marcbot.memory_candidate import format_memory_candidate_status

    message = format_memory_candidate_status()

    assert "MarcBot memory candidate status" in message
    assert "CLI commands:" in message
    assert "Telegram commands:" in message
    assert "memory candidate propose" in message
    assert "/memory_candidate_propose <project> | <text>" in message
    assert "Candidate propose writes pending proposals only." in message
    assert "Telegram cannot approve durable facts." in message
    assert "Provider contact: no" in message
    assert "Writes: no for this status command" in message
