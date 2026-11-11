#!/usr/bin/env bash
# Project-local Python setup. Never removes an existing environment or private data.
set -euo pipefail
saly_is_python312(){ "$1" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3,12))' >/dev/null 2>&1; }
saly_has_pip(){ "$1" -m pip --version >/dev/null 2>&1; }
saly_prepare_python(){
 local saly_root="$1" saly_python='' saly_candidate saly_uv='' saly_previous
 if [[ -n "${SALY_PYTHON:-}" ]]; then
  saly_python="$(command -v "$SALY_PYTHON")" || return 1
  if ! saly_is_python312 "$saly_python";then echo 'SALY requer Python 3.12. Ajuste SALY_PYTHON ou remova essa variável para seleção automática.' >&2;return 1;fi
 elif [[ -x "$saly_root/.venv/bin/python" ]] && saly_is_python312 "$saly_root/.venv/bin/python" && saly_has_pip "$saly_root/.venv/bin/python";then
  "$saly_root/.venv/bin/python" -m pip install --upgrade pip;return
 else
  for saly_candidate in python3.12 python3;do
   if command -v "$saly_candidate" >/dev/null && saly_is_python312 "$saly_candidate";then saly_python="$(command -v "$saly_candidate")";break;fi
  done
 fi
 if command -v uv >/dev/null;then saly_uv="$(command -v uv)";fi
 if [[ -z "$saly_python" ]] || ! "$saly_python" -c 'import ensurepip' >/dev/null 2>&1;then
  if [[ -z "$saly_uv" ]];then
   mkdir -p "$saly_root/.tools"
   if python3 -m pip --version >/dev/null 2>&1;then
    python3 -m pip install --only-binary=:all: --target "$saly_root/.tools/uv-bootstrap" 'uv==0.12.23'
    saly_uv="$saly_root/.tools/uv-bootstrap/bin/uv"
   else
    echo 'Python sem pip/ensurepip. Instale python3.12-venv (sudo apt-get install python3.12-venv) ou uv e repita. Seus dados permanecem intactos.' >&2;return 1
   fi
  fi
  export UV_PYTHON_INSTALL_DIR="${UV_PYTHON_INSTALL_DIR:-$saly_root/.tools/python}" UV_CACHE_DIR="${UV_CACHE_DIR:-$saly_root/.tools/cache}" UV_SYSTEM_CERTS=true
  if [[ -z "$saly_python" ]];then "$saly_uv" python install --no-bin 3.12;saly_python="$("$saly_uv" python find --managed-python --no-project 3.12)";fi
 fi
 if [[ -e "$saly_root/.venv" || -L "$saly_root/.venv" ]];then
  if [[ ! -x "$saly_root/.venv/bin/python" ]] || ! saly_is_python312 "$saly_root/.venv/bin/python" || ! saly_has_pip "$saly_root/.venv/bin/python";then
   saly_previous="$saly_root/.venv.previous.$(date +%Y%m%d%H%M%S).$$";mv "$saly_root/.venv" "$saly_previous";echo "Ambiente anterior preservado em $saly_previous"
  fi
 fi
 if [[ ! -x "$saly_root/.venv/bin/python" ]];then
  if [[ -n "$saly_uv" ]];then "$saly_uv" venv --seed --python "$saly_python" "$saly_root/.venv";else "$saly_python" -m venv "$saly_root/.venv";fi
 fi
 "$saly_root/.venv/bin/python" --version
 "$saly_root/.venv/bin/python" -m pip install --upgrade pip
}
