#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ ! -x backend/venv/bin/python ]; then
  echo "缺少项目 Python 环境，请先运行 ./setup-mac.sh" >&2
  exit 1
fi
if [ ! -f data/processed/catalog.sqlite ]; then
  backend/venv/bin/python scripts/build_catalog.py
fi
if [ ! -f frontend/build/index.html ]; then
  echo "缺少前端构建，请先按 README 执行 npm run build。" >&2
  exit 1
fi
echo "启动浙大小先生；默认访问 http://127.0.0.1:5000，Ctrl+C 停止。"
exec backend/venv/bin/python backend/app.py
