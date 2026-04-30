"""Tests for MarcBot health checks."""

from marcbot.health import HealthResult, format_health_report


def test_format_health_report_all_healthy() -> None:
    report = format_health_report(
        [
            HealthResult(True, "required runtime directories found"),
            HealthResult(True, "logs directory writable"),
            HealthResult(True, "config loads"),
        ],
    )

    assert "🤖 MarcBot health" in report
    assert "OK: required runtime directories found" in report
    assert "OK: logs directory writable" in report
    assert "OK: config loads" in report
    assert "Overall: healthy" in report


def test_format_health_report_unhealthy() -> None:
    report = format_health_report(
        [
            HealthResult(True, "required runtime directories found"),
            HealthResult(False, "config load failed"),
        ],
    )

    assert "OK: required runtime directories found" in report
    assert "ERROR: config load failed" in report
    assert "Overall: unhealthy" in report
