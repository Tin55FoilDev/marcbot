"""Local health checks for MarcBot."""

from __future__ import annotations

from dataclasses import dataclass

from marcbot.config import DEFAULT_CONFIG_PATH, load_config
from marcbot.paths import LOG_DIR, missing_runtime_dirs


@dataclass(frozen=True)
class HealthResult:
    """Result from a single health check."""

    ok: bool
    message: str


def check_runtime_dirs() -> HealthResult:
    """Check required runtime directories."""
    missing = missing_runtime_dirs()
    if missing:
        missing_list = ", ".join(str(path) for path in missing)
        return HealthResult(False, f"Missing required directories: {missing_list}")

    return HealthResult(True, "required runtime directories found")


def check_log_writeability() -> HealthResult:
    """Check that the log directory is writable."""
    test_file = LOG_DIR / ".health-write-test"

    try:
        test_file.write_text("ok\n", encoding="utf-8")
        test_file.unlink()
    except OSError:
        return HealthResult(False, f"logs directory is not writable: {LOG_DIR}")

    return HealthResult(True, "logs directory writable")


def check_config_loads() -> HealthResult:
    """Check that the local config file loads."""
    try:
        load_config(DEFAULT_CONFIG_PATH)
    except Exception as exc:
        return HealthResult(False, f"config load failed: {exc}")

    return HealthResult(True, "config loads")


def run_health_checks() -> list[HealthResult]:
    """Run local MarcBot health checks."""
    return [
        check_runtime_dirs(),
        check_log_writeability(),
        check_config_loads(),
    ]


def format_health_report(results: list[HealthResult]) -> str:
    """Format health check results for operator output."""
    lines = ["🤖 MarcBot health"]

    for result in results:
        prefix = "OK" if result.ok else "ERROR"
        lines.append(f"{prefix}: {result.message}")

    overall = "healthy" if all(result.ok for result in results) else "unhealthy"
    lines.append(f"Overall: {overall}")

    return "\n".join(lines)
