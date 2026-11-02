#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ -x .tools/node-v22.23.4-darwin-arm64/bin/node ]; then
  export PATH="$ROOT/.tools/node-v22.23.4-darwin-arm64/bin:$PATH"
fi
command -v npm >/dev/null || { echo "请先配置 Node 22 和 npm" >&2; exit 1; }
backend/venv/bin/python backend/app.py &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT INT TERM
cd frontend
npm start
