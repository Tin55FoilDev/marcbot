"""Tests for MarcBot service status helpers."""

from marcbot.service_status import ServiceStatus, format_service_report


def test_format_service_report() -> None:
    status = ServiceStatus(
        service_name="marcbot-telegram.service",
        active_state="active",
        enabled_state="enabled",
    )

    report = format_service_report(status)

    assert report == (
        "🤖 MarcBot service\n"
        "marcbot-telegram.service: active\n"
        "Boot enabled: enabled"
    )
