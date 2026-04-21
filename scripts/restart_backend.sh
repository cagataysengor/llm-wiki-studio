#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

if pgrep -f "uvicorn app.main:app --host 127.0.0.1 --port 8000" >/dev/null; then
  pkill -f "uvicorn app.main:app --host 127.0.0.1 --port 8000"
  sleep 1
fi

cd "$BACKEND_DIR"
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000

