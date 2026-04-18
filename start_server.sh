#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -z "${PYTHONPATH:-}" ]]; then
  export PYTHONPATH="$ROOT_DIR"
fi

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  exec "$ROOT_DIR/.venv/bin/python" -m src.app
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 -m src.app
fi

exec python -m src.app
