#!/usr/bin/env bash
# Explicit opt-in installer. Never run during ordinary SALY startup.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for saly_command in curl tar zstd; do
  command -v "$saly_command" >/dev/null || { echo "Dependência ausente: $saly_command. Instale-a antes de continuar."; exit 1; }
done
[[ -x .venv/bin/python ]] || { echo "Execute bash scripts/install.sh primeiro para criar a .venv."; exit 1; }
[[ "$(uname -s)" == Linux ]] || { echo 'Instalação automática disponível somente para Linux.'; exit 1; }
case "$(uname -m)" in x86_64) saly_arch=amd64;; aarch64) saly_arch=arm64;; *) echo 'Arquitetura não suportada'; exit 1;; esac
saly_free="$(df -Pk . | awk 'NR==2 {print $4}')"
[[ "$saly_free" -gt 17825792 ]] || { echo 'Reserve pelo menos 17 GiB livres para runtime, quatro modelos (~11 GiB estimados) e margem. Nenhum arquivo foi apagado.'; exit 1; }
echo "Arquitetura: $saly_arch; espaço livre: $saly_free KiB; limite de memória cgroup: $(cat /sys/fs/cgroup/memory.max 2>/dev/null || echo desconhecido)."
mkdir -p .tools/ollama/runtime
if [[ ! -x .tools/ollama/runtime/bin/ollama ]] && ! command -v ollama >/dev/null; then
  saly_installer=.tools/ollama/official-install.sh
  # Obtain the official installer for inspection, but use the documented manual binary
  # method below: no sudo, no system service, no change to user files.
  curl -fL --max-time 60 https://raw.githubusercontent.com/ollama/ollama/main/scripts/install.sh -o "$saly_installer"
  echo "Instalador oficial preservado para inspeção em $saly_installer; instalação manual oficial sem sudo."
  saly_archive=.tools/ollama/runtime.tar.zst
  curl -fL --retry 1 "https://github.com/ollama/ollama/releases/download/v0.40.16/ollama-linux-${saly_arch}.tar.zst" -o "$saly_archive"
  # CPU runtime, as verified in this environment; no GPU libraries are required.
  tar --zstd -xf "$saly_archive" -C .tools/ollama/runtime --exclude='lib/ollama/cuda*' --exclude='lib/ollama/rocm*' --exclude='lib/ollama/mlx*'
  rm "$saly_archive"
fi
bash scripts/start-ollama.sh
saly_binary="$(command -v ollama || true)"
[[ -n "$saly_binary" ]] || saly_binary="$PWD/.tools/ollama/runtime/bin/ollama"
"$saly_binary" --version
saly_available="$(.venv/bin/python - <<'CHECK'
from pathlib import Path
available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
try:
    maximum=Path('/sys/fs/cgroup/memory.max').read_text().strip()
    used=int(Path('/sys/fs/cgroup/memory.current').read_text())
    if maximum != 'max': available=min(available,int(maximum)-used)
except (OSError,ValueError): pass
print(available)
CHECK
)"
[[ "$saly_available" -ge 6442450944 ]] || { echo 'Menos de 6 GiB de RAM efetivamente livres: runtime instalado, modelos pendentes por recursos. Não alterei seu plano.'; exit 1; }
# Explicit sequential pulls, never parallel and never automatic paid fallback.
for saly_model in granite4:3b ministral-3:3b phi4-mini gemma3:4b; do
  saly_free="$(df -Pk . | awk 'NR==2 {print $4}')"
  [[ "$saly_free" -gt 7340032 ]] || { echo "Pendente $saly_model: menos de 7 GiB livres (peso + reserva)."; exit 1; }
  echo "Baixando/verificando $saly_model (gratuito local; sujeito à cota de computação do seu Codespaces)."
  OLLAMA_HOST=127.0.0.1:11434 "$saly_binary" pull "$saly_model" || { echo 'Download bloqueado/falhou; próximos modelos continuam pendentes. Nenhuma alternativa paga foi ativada.'; exit 1; }
done
# Native generation, one model at a time, recorded separately from mere installation.
.venv/bin/python scripts/probe-ollama.py
