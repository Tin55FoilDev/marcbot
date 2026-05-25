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
