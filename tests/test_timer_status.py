"""Tests for MarcBot timer status."""

from marcbot import timer_status


def test_parse_systemctl_show() -> None:
    parsed = timer_status._parse_systemctl_show(
        "Id=marcbot-backup.timer\n"
        "LoadState=loaded\n"
        "ActiveState=active\n"
        "LastTriggerUSec=\n",
    )

    assert parsed["Id"] == "marcbot-backup.timer"
    assert parsed["LoadState"] == "loaded"
    assert parsed["ActiveState"] == "active"
    assert parsed["LastTriggerUSec"] == ""


def test_clean_time_handles_empty_value() -> None:
    assert timer_status._clean_time("") == "never"


def test_timer_is_healthy_for_expected_states() -> None:
    timer = timer_status.UnitShowResult(
        fields={
            "LoadState": "loaded",
            "UnitFileState": "enabled",
            "ActiveState": "active",
            "SubState": "waiting",
        },
    )
    service = timer_status.UnitShowResult(
        fields={
            "LoadState": "loaded",
            "Result": "success",
            "ExecMainStatus": "0",
        },
    )

    assert timer_status._timer_is_healthy(timer, service) is True


def test_timer_is_not_healthy_when_disabled() -> None:
    timer = timer_status.UnitShowResult(
        fields={
            "LoadState": "loaded",
            "UnitFileState": "disabled",
            "ActiveState": "active",
            "SubState": "waiting",
        },
    )
    service = timer_status.UnitShowResult(
        fields={
            "LoadState": "loaded",
            "Result": "success",
            "ExecMainStatus": "0",
        },
    )

    assert timer_status._timer_is_healthy(timer, service) is False


def test_format_timer_status_message_with_stubbed_blocks(monkeypatch) -> None:
    calls = []

    def fake_format_timer_block(label: str, timer_name: str, service_name: str):
        calls.append((label, timer_name, service_name))
        return f"{label}: {timer_name}\n  Status: healthy", True

    monkeypatch.setattr(timer_status, "_format_timer_block", fake_format_timer_block)

    message = timer_status.format_timer_status_message()

    assert "🤖 MarcBot timer status" in message
    assert "Backup timer: marcbot-backup.timer" in message
    assert "Daily report timer: marcbot-daily-status-report.timer" in message
    assert "Overall: healthy" in message
    assert calls == list(timer_status.APPROVED_TIMERS)


def test_format_timer_status_message_warns_when_block_warns(monkeypatch) -> None:
    def fake_format_timer_block(label: str, timer_name: str, service_name: str):
        return f"{label}: {timer_name}\n  Status: warning", False

    monkeypatch.setattr(timer_status, "_format_timer_block", fake_format_timer_block)

    message = timer_status.format_timer_status_message()

    assert "Overall: warning - one or more timers need attention" in message
