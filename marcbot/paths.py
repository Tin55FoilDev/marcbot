"""Filesystem path helpers for MarcBot."""

from pathlib import Path

PROJECT_ROOT = Path("/srv/marcbot")
APP_DIR = PROJECT_ROOT / "app"
STATE_DIR = PROJECT_ROOT / "state"
WORKSPACE_DIR = PROJECT_ROOT / "workspace"
LOG_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"
BACKUP_DIR = PROJECT_ROOT / "backups"
TMP_DIR = PROJECT_ROOT / "tmp"

REQUIRED_RUNTIME_DIRS = (
    PROJECT_ROOT,
    APP_DIR,
    STATE_DIR,
    WORKSPACE_DIR,
    LOG_DIR,
    CONFIG_DIR,
    BACKUP_DIR,
    TMP_DIR,
)


def missing_runtime_dirs() -> list[Path]:
    """Return required MarcBot runtime directories that do not exist."""
    return [path for path in REQUIRED_RUNTIME_DIRS if not path.is_dir()]
