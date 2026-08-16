#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_ROOT="${SCRIPT_DIR}/runtime_env"
RELOCATOR="${ENV_ROOT}/relocate_portable_env.py"

if [ ! -d "${ENV_ROOT}" ]; then
  echo "[error] portable env not found: ${ENV_ROOT}" >&2
  return 1 2>/dev/null || exit 1
fi

if [ -f "${ENV_ROOT}/.portable_env_source_prefix.txt" ]; then
  if ! python "${RELOCATOR}"; then
    echo "[error] failed to relocate portable env" >&2
    return 1 2>/dev/null || exit 1
  fi
  if ! rm -f "${ENV_ROOT}/.portable_env_source_prefix.txt"; then
    echo "[warning] failed to remove relocation marker: ${ENV_ROOT}/.portable_env_source_prefix.txt" >&2
  fi
fi

if ! source "${ENV_ROOT}/bin/activate"; then
  echo "[error] failed to activate portable env: ${ENV_ROOT}/bin/activate" >&2
  return 1 2>/dev/null || exit 1
fi
