#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f frontend/dist/index.html || ! -x .venv/bin/python ]];then
 echo 'Execute bash scripts/install.sh primeiro.' >&2;exit 1
fi
umask 077
exec .venv/bin/python -m backend.serve
