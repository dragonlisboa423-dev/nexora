#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -f frontend/dist/index.html ] || [ ! -x .venv/bin/uvicorn ]; then
  echo 'Execute bash scripts/install.sh primeiro.' >&2
  exit 1
fi
# .env contains administrator-controlled configuration; never load it from imported documents.
if [ -f .env ]; then set -a; source .env; set +a; fi
export SALY_DATA_DIR="${SALY_DATA_DIR:-$PWD/data}"
umask 077
exec .venv/bin/uvicorn backend.main:app --host "${SALY_HOST:-127.0.0.1}" --port "${SALY_PORT:-8000}"
