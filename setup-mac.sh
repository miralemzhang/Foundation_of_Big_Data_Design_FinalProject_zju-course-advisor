#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
PY="$ROOT/.tools/python/cpython-3.11.18-macos-aarch64-none/bin/python3.11"
if [ ! -x "$PY" ]; then PY="$(command -v python3.11 || true)"; fi
if [ -z "$PY" ]; then echo "请先安装 Python 3.11（本机验证版本3.11.18）" >&2; exit 1; fi
"$PY" -c 'import sys; assert sys.version_info[:2] == (3,11), "需要Python 3.11"'
if [ ! -x backend/venv/bin/python ]; then "$PY" -m venv backend/venv; fi
backend/venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3,11), "已有venv版本不符，请重建"'
if [ -x .tools/uv/bin/uv ]; then
 .tools/uv/bin/uv pip install --python backend/venv/bin/python -r backend/requirements.lock.txt
else
 backend/venv/bin/python -m pip install -r backend/requirements.lock.txt
 backend/venv/bin/python -m pip check
fi
if [ -x .tools/node-v22.23.4-darwin-arm64/bin/node ]; then export PATH="$ROOT/.tools/node-v22.23.4-darwin-arm64/bin:$PATH"; fi
command -v node >/dev/null || { echo "请安装Node 22 LTS" >&2; exit 1; }
node -e 'if(process.versions.node.split(".")[0]!=="22")throw Error("需要Node 22")'
npm ci --prefix frontend --no-audit --no-fund
backend/venv/bin/python scripts/build_catalog.py
npm run build --prefix frontend
backend/venv/bin/python scripts/doctor.py --save
echo "环境和构建完成。运行 ./scripts/run-demo.sh；真实云端调用另以评测验证。"
