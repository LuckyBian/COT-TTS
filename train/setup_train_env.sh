#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_ROOT="${SCRIPT_DIR}/runtime_env"
PYTHON_BIN="${PYTHON_BIN:-python3}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu124}"

if [ ! -f "${SCRIPT_DIR}/requirements.txt" ]; then
  echo "[error] requirements.txt not found: ${SCRIPT_DIR}/requirements.txt" >&2
  exit 1
fi

if [ ! -d "${ENV_ROOT}" ]; then
  "${PYTHON_BIN}" -m venv "${ENV_ROOT}"
fi

source "${ENV_ROOT}/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install --extra-index-url "${TORCH_INDEX_URL}" -r "${SCRIPT_DIR}/requirements.txt"
python -m pip install -e "${SCRIPT_DIR}"

echo "[done] environment ready: ${ENV_ROOT}"
echo "[next] source ${ENV_ROOT}/bin/activate"
