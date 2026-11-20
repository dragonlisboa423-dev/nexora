#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
umask 077
if curl --noproxy '*' -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo 'Ollama já responde em localhost:11434; não alterei o serviço existente.'
  exit 0
fi
saly_binary="$(command -v ollama || true)"
if [[ -z "$saly_binary" && -x .tools/ollama/runtime/bin/ollama ]]; then
  saly_binary="$PWD/.tools/ollama/runtime/bin/ollama"
fi
if [[ -z "$saly_binary" ]]; then echo 'Execute bash scripts/setup-ollama.sh primeiro.'; exit 1; fi
saly_runtime="$PWD/.tools/ollama"
mkdir -p "$saly_runtime/models" "$saly_runtime/home"
chmod 700 "$saly_runtime" "$saly_runtime/models" "$saly_runtime/home"
# Create the log synchronously before the background redirect can race chmod.
# Append preserves earlier startup diagnostics on restart.
: >> "$saly_runtime/server.log"
chmod 600 "$saly_runtime/server.log"
# A clean environment prevents cloud/provider credentials from reaching the runtime.
# Only loopback; no public forwarding. A single loaded model and a single generation.
nohup env -i PATH=/usr/bin:/bin HOME="$saly_runtime/home" OLLAMA_HOST=127.0.0.1:11434 \
  OLLAMA_MODELS="$saly_runtime/models" OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 \
  OLLAMA_KEEP_ALIVE=0 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_NO_CLOUD=1 \
  "$saly_binary" serve >>"$saly_runtime/server.log" 2>&1 </dev/null &
printf '%s\n' "$!" > "$saly_runtime/server.pid"
chmod 600 "$saly_runtime/server.pid"
for saly_attempt in {1..50}; do
  if curl --noproxy '*' -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "Ollama iniciado em 127.0.0.1:11434 (PID $(cat "$saly_runtime/server.pid"))."; exit 0
  fi
  sleep .2
done
echo 'Servidor não iniciou. Consulte .tools/ollama/server.log (privado).'; exit 1
