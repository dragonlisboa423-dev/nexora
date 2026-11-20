# Qwen como modelo principal — auditoria e entrega

## Origem confirmada e limite da recuperação

Foi consultado o histórico completo disponível (clone não raso), incluindo as branches remotas, e procuradas ocorrências de `qwen2.5:3b`/Qwen nas versões. **Não foi encontrada uma configuração versionada de Qwen 2.5 3B como modelo antigo.** A primeira implementação local, `0be7dc1`, tinha `SALY_MODEL=smollm3:3b` em `.env.example` e HTTP/NDJSON nativo do Ollama (`backend/main.py`, `/api/chat`). As ocorrências versionadas de Qwen encontradas em `fc80aba` são uma tabela de provedores/preços, não configuração ativa.

A captura anterior fornecida pelo proprietário mostra `qwen/qwen3.8-27b`, escolhido no catálogo do **Groq**. Ela não comprova `qwen2.5:3b` no Ollama. Configurações privadas do Codespace excluído não estão no Git. O ZIP antigo anexado anteriormente também não pôde ser resolvido pela ferramenta de arquivos nesta sessão. Não foi apresentada uma recriação como recuperação de uma variante comprovada.

Foi configurado **o alvo explicitamente solicitado**, `qwen2.5:3b`, reutilizando o adaptador Ollama já existente, sem rollback de projeto. A correção mais recente do pedido (“NÃO preserve o Phi”) prevalece sobre a linha repetida que o menciona como secundário: Phi foi retirado da seleção; **Gemma 3 4B** é alternativa opcional. Granite/Ministral continuam opcionais se já instalados. Nenhum peso ou dado anterior foi excluído.

## Comportamento e preservação

- Padrão local: `qwen2.5:3b`. Uma migração pequena e executada uma única vez registra o padrão anterior e seleciona Qwen. Escolhas manuais posteriores de outro modelo continuam persistentes.
- Conversas antigas que apontam para `phi4-mini` passam a resolver a seleção como Qwen. Os registros históricos das respostas continuam identificando o modelo que realmente os produziu; não são reescritos. Memórias, documentos, conversas, credenciais e revisões são preservados.
- Phi não aparece no catálogo/seletor nem pode ser escolhido pela API de conversa. Seus pesos existentes não são apagados. A comparação opcional por CLI pode usá-lo somente como diagnóstico, sem readicioná-lo à interface e sem baixar pesos.
- O mesmo fluxo de Core, memórias autorizadas, Centro Smolin, voz e streaming é mantido. O protocolo continua `stream=true`, com fragmentos de texto reais; heartbeats de transporte não são texto gerado.
- Respostas completas usam `keep_alive=300` segundos: o modelo pode ser reutilizado nas mensagens seguintes. O servidor iniciado pelo script mantém um modelo carregado e uma geração por vez. O runtime pode evictar por RAM ou troca de modelo; não se promete residência garantida contra pressão de memória. Falha ou cancelamento ainda solicita descarregamento. Um servidor externo que já responde não é reiniciado à força.
- Leitura do runtime: 300 s de espera entre dados; prazo total do chat local: 600 s por padrão. O transporte segue enviando heartbeats durante a carga. Limites são finitos e configuráveis, sem repetição automática de mensagens, geração simulada ou serviço pago.
- O estado autenticado `/api/health` identifica o modelo e o destino real configurado: `runtime.kind=ollama-server-local`, endpoint loopback `http://127.0.0.1:11434`, hostname e `CODESPACE_NAME` quando disponível. Disponibilidade/geração comprovada continua separada da escolha do modelo.

Variáveis opcionais, sem alterar o `.env` existente:

```dotenv
SALY_OLLAMA_KEEP_ALIVE_SECONDS=300
SALY_LOCAL_CHAT_TIMEOUT_SECONDS=600
```

## Ambiente realmente verificado nesta sessão

O workspace **Codex**, hostname `0abddb8c8c09`, é separado do Codespace do proprietário. Nele, o Ollama nativo **0.40.16** respondeu em loopback e o catálogo estava vazio. Foi executado o comando oficial solicitado:

```bash
OLLAMA_HOST=127.0.0.1:11434 .tools/ollama/runtime/bin/ollama pull qwen2.5:3b
```

O download falhou com recusa de resolução DNS de `registry.ollama.ai`. A consulta HTTPS pelo proxy também retornou CONNECT HTTP 403. Nenhum mirror, credencial inventada ou serviço pago foi usado. Não existe ferramenta conectada para operar diretamente o Codespace privado do proprietário nesta sessão; não foi alegada instalação nele.

**Nenhum modelo executou uma resposta química real neste workspace.** O padrão do código agora é Qwen, mas isso não implica que o processo ainda em execução no Codespace já tenha recebido o código/pesos. O relatório nativo sanitizado está em [SALY_QWEN_RUNTIME_CHECK.json](SALY_QWEN_RUNTIME_CHECK.json).

| Teste real solicitado | Situação neste workspace | Primeiro trecho visível | Duração total |
|---|---|---|---|
| Qwen 2.5 3B — água | Bloqueado: peso ausente e download recusado | Não medido | Não medida |
| Phi-4 Mini — comparação opcional | Peso ausente | Não medido | Não medida |

Não há base para declarar Qwen mais rápido que Phi, qualidade científica aprovada ou ausência de travamentos no hardware do proprietário. Os números de testes com protocolo controlado não são benchmarks de inferência.

## Aplicar no Codespace e medir

No terminal que executa a SALY, interrompa o servidor com Ctrl+C. Depois:

```bash
cd /workspaces/nexora
git pull --ff-only
bash scripts/setup-ollama.sh
SALY_SECURE_COOKIE=1 bash scripts/start.sh
```

O instalador reutiliza o runtime, baixa Qwen e tenta Gemma como alternativa se houver disco. Falha do Gemma opcional não impede testar o Qwen; falha do Qwen é informada e interrompe a instalação. Mantidas as verificações de RAM/disco; pesos antigos não são removidos para liberar espaço. O teste padrão termina com Qwen, favorecendo sua reutilização em seguida. Se o instalador for executado outra vez enquanto um modelo já ocupa RAM, a verificação de memória livre pode interrompê-lo; aguarde a expiração do cache ou use diretamente o diagnóstico dos pesos já instalados, sem reinstalar. O início reconstrói a interface se necessário; atualize a página/PWA.

Também é possível iniciar o runtime e baixar **somente** Qwen explicitamente, mantendo as verificações de recursos do ambiente sob responsabilidade do operador:

```bash
bash scripts/start-ollama.sh
saly_ollama="$(command -v ollama || printf '%s' "$PWD/.tools/ollama/runtime/bin/ollama")"
"$saly_ollama" pull qwen2.5:3b
```

O comando de diagnóstico usa por padrão a pergunta exata:

> Explique quimicamente a molécula de água e suas propriedades.

```bash
.venv/bin/python scripts/probe-ollama.py qwen2.5:3b --repeat 2
```

Cada execução concluída imprime a resposta e registra `first_token_seconds` (primeiro trecho não vazio), `seconds` (duração total da chamada ao runtime), digest, métricas nativas e ambiente. `load_duration`/`eval_duration` nativos são nanosegundos. A primeira execução pode já estar aquecida; a segunda permite observar reutilização, sem assumir que a primeira foi necessariamente fria. O relatório fica em `.tools/ollama/probe.json`, privado e ignorado pelo Git. Essas medidas são do adaptador/Ollama, sem incluir toda a latência de RAG/navegador; não são uma avaliação científica do conteúdo.

Para comparar apenas se os pesos anteriores do Phi ainda estiverem instalados:

```bash
.venv/bin/python scripts/probe-ollama.py qwen2.5:3b --repeat 2 --compare-phi
```

Phi é medido antes do Qwen para terminar com o principal aquecido. Modelo ausente é marcado como tal, sem baixar Phi nem inventar resposta/tempos. Ctrl+C preserva os pesos e amostras já concluídas.

## Verificação do código

- Backend: **193 testes aprovados**, um PostgreSQL ignorado por falta de serviço. Migração de padrão, histórico original intacto, Phi rejeitado no seletor, novos padrões, TTFT/duração, ausência de descarregamento no sucesso e limpeza em erros/cancelamento.
- Frontend: **25 testes Vitest aprovados** e build de produção concluído; aviso conhecido sobre tamanho do bundle permanece. Ruff, sintaxe Bash e diff verificados.
- Chromium/protocolo **controlado**: `browser_model_selection.py` passa a pergunta exata pelo fluxo completo da SALY com Qwen selecionado, alterna para Gemma, testa o registro do CLI no banco, preserva histórico e verifica celular. Não é resposta de pesos reais.
- `browser_chat_network.py`: streaming atrasado através de proxy com corte por inatividade, heartbeats, desconexão sem repetição/falsa conclusão. `browser_integrated_update.py`: ZIP, bytes privados, núcleo, transparência e layout móvel preservados.
