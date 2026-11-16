#!/usr/bin/env bash
# Optional, explicit local speech engine. Never runs during normal app installation/start.
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python -m pip install --index-url https://download.pytorch.org/whl/cpu torch
.venv/bin/python -m pip install 'openai-whisper==20250625'
.venv/bin/python - <<'PY'
import hashlib
import os
import urllib.request
from pathlib import Path
from backend.smolin.transcription import MODEL_SHA,MODEL_URL,model_path
path=model_path()
path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
if path.exists():
    with path.open('rb') as source:
        if hashlib.file_digest(source,'sha256').hexdigest()==MODEL_SHA:
            print('Modelo local já verificado.');raise SystemExit()
    raise SystemExit('Arquivo existente tem hash diferente; não será substituído automaticamente.')
temporary=path.with_suffix('.download')
try:
    with urllib.request.urlopen(MODEL_URL,timeout=60) as response, temporary.open('xb') as target:
        size=0
        while chunk:=response.read(1024*1024):
            size+=len(chunk)
            if size>100*1024*1024:raise ValueError('Modelo acima do limite')
            target.write(chunk)
    with temporary.open('rb') as source:
        if hashlib.file_digest(source,'sha256').hexdigest()!=MODEL_SHA:raise ValueError('Checksum divergente')
    temporary.chmod(0o600);os.replace(temporary,path)
finally:
    temporary.unlink(missing_ok=True)
print('Modelo tiny local instalado e checksum verificado. Use Transcrever fala no Smolin para testar seu arquivo.')
PY
