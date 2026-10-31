#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
(cd frontend && npm run build)
.venv/bin/python -m pytest backend/tests -q
