"""Tests for approved MarcBot timer visibility."""

from marcbot.timer_status import APPROVED_TIMERS


def test_source_monitor_timer_is_approved_for_timer_status() -> None:
    approved_timer_names = {timer_name for _label, timer_name, _service_name in APPROVED_TIMERS}
    approved_service_names = {
        service_name for _label, _timer_name, service_name in APPROVED_TIMERS
    }

    assert "marcbot-source-monitor-ai.timer" in approved_timer_names
    assert "marcbot-source-monitor-ai.service" in approved_service_names
