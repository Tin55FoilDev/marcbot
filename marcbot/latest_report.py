"""Find the latest local MarcBot daily status report."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marcbot.paths import WORKSPACE_DIR

REPORTS_DIR = WORKSPACE_DIR / "reports"
DAILY_STATUS_GLOB = "daily-status-*.md"


@dataclass(frozen=True)
class LatestReportResult:
    """Result of looking up the latest generated report."""

    ok: bool
    message: str
    path: Path | None = None


def find_latest_daily_status_report(reports_dir: Path = REPORTS_DIR) -> Path | None:
    """Return the newest daily status report by modification time."""
    try:
        candidates = [path for path in reports_dir.glob(DAILY_STATUS_GLOB) if path.is_file()]
    except OSError:
        return None

    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)


def validate_latest_daily_status_report(reports_dir: Path = REPORTS_DIR) -> LatestReportResult:
    """Validate that a latest daily status report exists and can be sent."""
    if not reports_dir.is_dir():
        return LatestReportResult(
            ok=False,
            message=(
                "🤖 MarcBot latest report\n"
                f"Reports directory is missing: {reports_dir}"
            ),
        )

    latest = find_latest_daily_status_report(reports_dir=reports_dir)

    if latest is None:
        return LatestReportResult(
            ok=False,
            message=(
                "🤖 MarcBot latest report\n"
                "No daily status reports found.\n"
                "Generate one with: python -m marcbot report daily-status"
            ),
        )

    if not latest.is_file():
        return LatestReportResult(
            ok=False,
            message=(
                "🤖 MarcBot latest report\n"
                f"Latest report is not a regular file: {latest}"
            ),
        )

    return LatestReportResult(
        ok=True,
        message=f"Latest daily status report: {latest.name}",
        path=latest,
    )
