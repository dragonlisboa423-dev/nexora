#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f frontend/dist/index.html || ! -x .venv/bin/python ]];then
 echo 'Execute bash scripts/install.sh primeiro.' >&2;exit 1
fi
# A git pull updates sources, not the ignored dist/ directory. Rebuild before
# serving when the UI inputs are newer, so the running app has the new controls.
saly_frontend_stale="$(.venv/bin/python - <<'CHECK'
from pathlib import Path
built = Path("frontend/dist/index.html").stat().st_mtime_ns
inputs = [Path("frontend/index.html"), Path("frontend/package.json"), Path("frontend/package-lock.json"), Path("frontend/vite.config.ts")]
for folder in ("frontend/src", "frontend/public"):
    inputs.extend(path for path in Path(folder).rglob("*") if path.is_file())
print("yes" if any(path.exists() and path.stat().st_mtime_ns > built for path in inputs) else "no")
CHECK
)"
if [[ "$saly_frontend_stale" == yes ]]; then
  command -v npm >/dev/null || { echo 'Interface desatualizada. Execute bash scripts/install.sh para preparar o frontend.' >&2; exit 1; }
  echo 'Atualizando a interface após alterações no projeto…'
  npm --prefix frontend run build
fi
umask 077
exec .venv/bin/python -m backend.serve
