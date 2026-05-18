"""Read-only status reporting for MarcBot systemd timers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

APPROVED_TIMERS: tuple[tuple[str, str, str], ...] = (
    ("Backup timer", "marcbot-backup.timer", "marcbot-backup.service"),
    (
        "AI source monitor timer",
        "marcbot-source-monitor-ai.timer",
        "marcbot-source-monitor-ai.service",
    ),
    (
        "Daily report timer",
        "marcbot-daily-status-report.timer",
        "marcbot-daily-status-report.service",
    ),
    (
        "Daily report send timer",
        "marcbot-daily-status-report-send.timer",
        "marcbot-daily-status-report-send.service",
    ),
    (
        "Weather report timer",
        "marcbot-weather-report.timer",
        "marcbot-weather-report.service",
    ),
)

TIMER_FIELDS: tuple[str, ...] = (
    "Id",
    "LoadState",
    "ActiveState",
    "SubState",
    "UnitFileState",
    "NextElapseUSecRealtime",
    "LastTriggerUSec",
)

SERVICE_FIELDS: tuple[str, ...] = (
    "Id",
    "LoadState",
    "ActiveState",
    "SubState",
    "Result",
    "ExecMainStatus",
)


@dataclass(frozen=True)
class UnitShowResult:
    """Parsed subset of systemctl show output."""

    fields: dict[str, str]
    error: str | None = None


def _parse_systemctl_show(output: str) -> dict[str, str]:
    """Parse simple KEY=VALUE systemctl show output."""
    parsed: dict[str, str] = {}

    for line in output.splitlines():
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        parsed[key] = value

    return parsed


def _systemctl_show(unit_name: str, fields: tuple[str, ...]) -> UnitShowResult:
    """Return selected systemctl show fields for a unit."""
    command = ["systemctl", "show", unit_name, "--no-pager"]

    for field in fields:
        command.extend(["-p", field])

    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except OSError as exc:
        return UnitShowResult(fields={}, error=str(exc))
    except subprocess.TimeoutExpired:
        return UnitShowResult(fields={}, error="systemctl timed out")

    if result.returncode != 0:
        error = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"systemctl exited {result.returncode}"
        )
        return UnitShowResult(fields={}, error=error)

    return UnitShowResult(fields=_parse_systemctl_show(result.stdout))


def _clean_time(value: str) -> str:
    """Return a readable time value for systemctl timestamp fields."""
    if not value:
        return "never"

    return value


def _timer_is_healthy(timer: UnitShowResult, service: UnitShowResult) -> bool:
    """Return whether one MarcBot timer/service pair looks healthy."""
    if timer.error or service.error:
        return False

    timer_fields = timer.fields
    service_fields = service.fields

    return (
        timer_fields.get("LoadState") == "loaded"
        and timer_fields.get("UnitFileState") == "enabled"
        and timer_fields.get("ActiveState") == "active"
        and timer_fields.get("SubState") == "waiting"
        and service_fields.get("LoadState") == "loaded"
        and service_fields.get("Result") in {"success", ""}
        and service_fields.get("ExecMainStatus") in {"0", ""}
    )


def _format_timer_block(label: str, timer_name: str, service_name: str) -> tuple[str, bool]:
    """Format one timer/service status block."""
    timer = _systemctl_show(timer_name, TIMER_FIELDS)
    service = _systemctl_show(service_name, SERVICE_FIELDS)
    healthy = _timer_is_healthy(timer, service)

    lines = [f"{label}: {timer_name}"]

    if timer.error:
        lines.append(f"  Timer error: {timer.error}")
    else:
        timer_fields = timer.fields
        lines.extend(
            [
                f"  Enabled: {timer_fields.get('UnitFileState', 'unknown')}",
                f"  Active: {timer_fields.get('ActiveState', 'unknown')}"
                f" ({timer_fields.get('SubState', 'unknown')})",
                f"  Next run: {_clean_time(timer_fields.get('NextElapseUSecRealtime', ''))}",
                f"  Last timer trigger: {_clean_time(timer_fields.get('LastTriggerUSec', ''))}",
            ],
        )

    if service.error:
        lines.append(f"  Service error: {service.error}")
    else:
        service_fields = service.fields
        lines.extend(
            [
                f"  Service: {service_name}",
                f"  Last service result: {service_fields.get('Result', 'unknown')}",
                f"  Last exit status: {service_fields.get('ExecMainStatus', 'unknown')}",
            ],
        )

    if healthy:
        lines.append("  Status: healthy")
    else:
        lines.append("  Status: warning")

    return "\n".join(lines), healthy


def format_timer_status_message() -> str:
    """Return Telegram-ready status for approved MarcBot timers."""
    lines = ["🤖 MarcBot timer status"]
    all_healthy = True

    for label, timer_name, service_name in APPROVED_TIMERS:
        block, healthy = _format_timer_block(label, timer_name, service_name)
        lines.append("")
        lines.append(block)

        if not healthy:
            all_healthy = False

    lines.append("")
    if all_healthy:
        lines.append("Overall: healthy")
    else:
        lines.append("Overall: warning - one or more timers need attention")

    return "\n".join(lines)
