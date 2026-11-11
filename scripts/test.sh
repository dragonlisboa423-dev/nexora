#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npm --prefix frontend run build
npm --prefix frontend test
.venv/bin/python -m pytest backend/tests -q
