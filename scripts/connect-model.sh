#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]];then
 echo 'Execute bash scripts/install.sh primeiro.' >&2;exit 1
fi
exec .venv/bin/python -m backend.connect_model "$@"
