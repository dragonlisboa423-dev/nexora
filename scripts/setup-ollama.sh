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
[[ "$saly_free" -gt 7340032 ]] || { echo 'Reserve pelo menos 7 GiB livres para runtime, Qwen 2.5 3B e margem; Gemma será opcional. Nenhum arquivo foi apagado.'; exit 1; }
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
echo "RAM efetivamente disponível: $((saly_available / 1024 / 1024)) MiB; mínimo para tentar os modelos: 5120 MiB."
[[ "$saly_available" -ge 5368709120 ]] || { echo 'Menos de 5 GiB de RAM efetivamente livres: runtime instalado, modelos pendentes por recursos. Não alterei seu plano.'; exit 1; }
# Explicit sequential pulls, never parallel and never automatic paid fallback.
for saly_model in qwen2.5:3b gemma3:4b; do
  saly_free="$(df -Pk . | awk 'NR==2 {print $4}')"
  if [[ "$saly_free" -le 7340032 ]]; then
    echo "Pendente $saly_model: menos de 7 GiB livres (peso + reserva)."
    [[ "$saly_model" == gemma3:4b ]] && continue
    exit 1
  fi
  echo "Baixando/verificando $saly_model (gratuito local; sujeito à cota de computação do seu Codespaces)."
  if ! OLLAMA_HOST=127.0.0.1:11434 "$saly_binary" pull "$saly_model"; then
    echo "Download de $saly_model indisponível; nenhum provedor alternativo foi ativado."
    [[ "$saly_model" == gemma3:4b ]] && continue
    exit 1
  fi
done
# Native generation, one model at a time, recorded separately from mere installation.
.venv/bin/python scripts/probe-ollama.py qwen2.5:3b
