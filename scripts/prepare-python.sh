#!/usr/bin/env bash
# Sourced by install.sh. All paths are relative to the existing checkout.
# Use the tested minor version; older pydantic-core wheels cannot target every new CPython.
set -euo pipefail

saly_is_python312() {
  "$1" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 12))' >/dev/null 2>&1
}

saly_prepare_python() {
  local saly_root="$1" saly_python="" saly_candidate saly_uv saly_previous
  if [[ -n "${SALY_PYTHON:-}" ]]; then
    saly_python="$(command -v "$SALY_PYTHON")" || {
      echo "SALY_PYTHON não aponta para um interpretador executável." >&2
      return 1
    }
    if ! saly_is_python312 "$saly_python"; then
      echo "SALY requer Python 3.12. Ajuste SALY_PYTHON ou remova essa variável para seleção automática." >&2
      return 1
    fi
  elif [[ -x "$saly_root/.venv/bin/python" ]] && saly_is_python312 "$saly_root/.venv/bin/python"; then
    saly_python="$saly_root/.venv/bin/python"
  else
    for saly_candidate in python3.12 python3; do
      if command -v "$saly_candidate" >/dev/null && saly_is_python312 "$saly_candidate"; then
        saly_python="$(command -v "$saly_candidate")"
        break
      fi
    done
  fi

  if [[ -z "$saly_python" ]]; then
    echo 'Python 3.12 não encontrado. Preparando runtime local com uv…'
    mkdir -p "$saly_root/.tools"
    if command -v uv >/dev/null; then
      saly_uv="$(command -v uv)"
    else
      # Isolated bootstrap: never installs into the system Python or executes a remote shell script.
      if [[ ! -x "$saly_root/.tools/bootstrap/bin/python" ]]; then
        python3 -m venv "$saly_root/.tools/bootstrap"
      fi
      "$saly_root/.tools/bootstrap/bin/python" -m pip install --only-binary=:all: 'uv==0.12.23'
      saly_uv="$saly_root/.tools/bootstrap/bin/uv"
    fi
    export UV_PYTHON_INSTALL_DIR="${UV_PYTHON_INSTALL_DIR:-$saly_root/.tools/python}"
    export UV_CACHE_DIR="${UV_CACHE_DIR:-$saly_root/.tools/cache}"
    # Use platform trust in addition to the packaged roots. TLS/checksum checks remain enabled.
    export UV_SYSTEM_CERTS=true
    "$saly_uv" python install --no-bin 3.12
    saly_python="$("$saly_uv" python find --managed-python --no-project 3.12)"
    saly_is_python312 "$saly_python" || return 1
  fi

  if [[ -e "$saly_root/.venv" || -L "$saly_root/.venv" ]]; then
    if [[ ! -x "$saly_root/.venv/bin/python" ]] || ! saly_is_python312 "$saly_root/.venv/bin/python"; then
      saly_previous="$saly_root/.venv.previous.$(date +%Y%m%d%H%M%S).$$"
      mv "$saly_root/.venv" "$saly_previous"
      echo "Ambiente Python anterior preservado em $saly_previous"
    fi
  fi
  if [[ ! -x "$saly_root/.venv/bin/python" ]]; then
    "$saly_python" -m venv "$saly_root/.venv"
  fi
  "$saly_root/.venv/bin/python" --version
  "$saly_root/.venv/bin/python" -m pip install --upgrade pip
}
