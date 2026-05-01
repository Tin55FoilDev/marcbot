"""Read-only systemd service status helpers for MarcBot."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

SERVICE_NAME = "marcbot-telegram.service"
SYSTEMCTL_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class ServiceStatus:
    """Read-only status for one systemd service."""

    service_name: str
    active_state: str
    enabled_state: str


def _run_systemctl(args: list[str]) -> str:
    """Run a fixed systemctl query and return compact output."""
    result = subprocess.run(
        ["systemctl", *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=SYSTEMCTL_TIMEOUT_SECONDS,
    )

    output = (result.stdout or result.stderr).strip()
    if not output:
        return "unknown"

    return output.splitlines()[0].strip() or "unknown"


def get_service_status(service_name: str = SERVICE_NAME) -> ServiceStatus:
    """Return active and enabled status for the MarcBot systemd service."""
    active_state = _run_systemctl(["is-active", service_name])
    enabled_state = _run_systemctl(["is-enabled", service_name])

    return ServiceStatus(
        service_name=service_name,
        active_state=active_state,
        enabled_state=enabled_state,
    )


def format_service_report(status: ServiceStatus | None = None) -> str:
    """Format a Telegram-friendly service status report."""
    if status is None:
        status = get_service_status()

    return (
        "🤖 MarcBot service\n"
        f"{status.service_name}: {status.active_state}\n"
        f"Boot enabled: {status.enabled_state}"
    )
