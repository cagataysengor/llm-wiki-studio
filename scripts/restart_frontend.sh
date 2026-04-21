#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

if pgrep -f "next dev --hostname 127.0.0.1 --port 3000" >/dev/null; then
  pkill -f "next dev --hostname 127.0.0.1 --port 3000"
  sleep 1
fi

cd "$FRONTEND_DIR"
exec npm run dev -- --hostname 127.0.0.1 --port 3000

