#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x ".venv/bin/python" ]]; then
  echo "ERROR [MBOT-CLI-001]: Python virtual environment not found at .venv" >&2
  echo "Run: python3 -m venv .venv" >&2
  exit 1
fi

. .venv/bin/activate

echo "===== MarcBot version ====="
python -m marcbot --version

echo
echo "===== MarcBot doctor ====="
python -m marcbot doctor

echo
echo "===== pytest ====="
pytest -q

echo
echo "===== ruff ====="
ruff check .

echo
echo "All MarcBot checks passed."
