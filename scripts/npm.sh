#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -x "$ROOT/.tools/node-v22.23.4-darwin-arm64/bin/node" ]; then
  export PATH="$ROOT/.tools/node-v22.23.4-darwin-arm64/bin:$PATH"
fi
command -v npm >/dev/null || { echo "请先配置Node 22和npm" >&2; exit 1; }
cd "$ROOT/frontend"
exec npm "$@"
