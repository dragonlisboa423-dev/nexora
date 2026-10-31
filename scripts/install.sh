#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/prepare-python.sh
saly_prepare_python "$PWD"
# Fail clearly on unsupported platforms instead of trying to compile the Rust extension.
.venv/bin/python -m pip install --only-binary=pydantic-core -r backend/requirements.txt
(cd frontend && npm ci && npm run build)
.venv/bin/python -m backend.manage init
