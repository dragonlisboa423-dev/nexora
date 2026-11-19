# SALY — atualização integrada (19/11/2026)

## Escopo e estado real

Base auditada: `0dff8a9`, branch `feat/saly-smolin`; ponto de recuperação local `recovery/pre-integrated-0dff8a9`. Não houve reset, reconstrução da interface, troca do núcleo por folha, alteração de credenciais ou de dados pessoais. Este ambiente do Codex **não é o Codespace do proprietário**. Um push não instala modelos nem reinicia o site do Codespace.

| Parte | Entrega | Limitação comprovada |
|---|---|---|
| Ollama | Runtime oficial CPU 0.40.16 instalado e servidor testado em localhost; instalador reproduzível, downloads sequenciais e diagnósticos | Registro inacessível nesta rede; nenhum dos quatro modelos instalado/funcional |
| Seleção | Chat e Configurações → Sistema; padrão persistente e escolha por conversa; histórico e metadados de cada resposta preservados | Inferência com pesos reais bloqueada; integração de transporte validada com respostas controladas em testes, claramente distintas de inferência real |
| Memória/RAG local | Mesmo Core, memórias autorizadas e busca textual/LSA, contexto limitado; sem embeddings remotos ao selecionar Ollama | Ferramentas de agente e visão dos modelos locais não verificadas e desabilitadas; não declarar execução de operações por esses modelos |
| Núcleo | Esfera original mantida, batimento regional e secundário no shader, circulação luminosa, fibras internas, controles, bloom de qualidade alta | Desempenho depende do aparelho; navegador de teste usa SwiftShader, sem comprovação de FPS em GPU/Android físico |
| ZIP | Conteúdo interno extraído localmente, indexação por página, árvore, abrir/baixar membros, referências arquivo/página e exclusão derivada | Limites explícitos, sem ZIP64, senhas, ZIP recursivo ou execução; imagens usam OCR, sem compreensão generativa verificada |

## Ollama: medição e bloqueio

Ambiente medido: Linux x86_64, CPU cgroup 4 núcleos (host `nproc=5`), RAM cgroup 32 GiB, aproximadamente 32 GiB disponíveis na inspeção inicial, sem swap/GPU detectável; disco overlay 63 GiB, 47 GiB livres. Python 3.12.14; Node 24.19.0. Não foi consultada/alterada a cobrança da conta Codespaces.

`https://ollama.com/install.sh` retornou HTTP 403. O instalador oficial em `https://raw.githubusercontent.com/ollama/ollama/main/scripts/install.sh` foi obtido e inspecionado, sem execução via sudo. Alternativa manual oficial utilizada: `https://github.com/ollama/ollama/releases/download/v0.40.16/ollama-linux-amd64.tar.zst`. Foram extraídos apenas runtime e bibliotecas de CPU em `.tools/ollama/runtime` (116 MiB), excluindo CUDA/ROCm/MLX. O arquivo baixado tem SHA-256 local `87bfafb2acbc89b2e6a1be0a9043de6aa75fb450696f86bc426e65fc448f788d`; esse cálculo identifica o download e **não é uma comparação com checksum publicado pelo mantenedor**.

Servidor nativo respondeu `/api/version` com `0.40.16` e `/api/tags` com `{"models":[]}`. `ollama pull granite4:3b` falhou ao consultar `registry.ollama.ai`: resolução DNS recusada no runtime isolado; a consulta HTTPS pelo proxy deste ambiente também recebeu CONNECT 403. Os próximos downloads não foram iniciados em paralelo nem substituídos por serviços pagos.

| Modelo solicitado | Instalado | Geração portuguesa | Ferramentas | Visão | Peso local / latência de inferência |
|---|---|---|---|---|---|
| `granite4:3b` | Não | Não realizada | Não verificado | Não verificada | Nenhum / indisponível |
| `ministral-3:3b` | Não | Não realizada | Não verificado | Não verificada | Nenhum / indisponível |
| `phi4-mini` | Não | Não realizada | Não verificado | Não verificada | Nenhum / indisponível |
| `gemma3:4b` | Não | Não realizada | Não verificado | Não verificada | Nenhum / indisponível |

Com servidor ativo, os quatro pedidos nativos de geração falharam com HTTP 404 por modelo ausente. Respostas sanitizadas registradas em `docs/SALY_LOCAL_MODEL_STATUS_2026.json`. Milissegundos até um erro **não são** medidas de geração. Não há respostas científicas, uso de RAM por modelo ou capacidade multimodal confirmados. A existência dessas tags no catálogo atual também não pôde ser confirmada. O runtime de teste foi encerrado pelo ciclo de execução do ambiente; o script de reinício permanece disponível. Não enviar dados privados para um serviço externo como alternativa ao bloqueio.

A seleção usa somente IDs permitidos, backend autenticado e loopback fixo; o frontend não consulta a porta 11434. O cliente local ignora proxies e redirects. Uma geração local por vez; servidor iniciado pelo script configurado com um modelo carregado e `keep_alive=0`; solicita-se descarregamento também ao terminar/cancelar. Contexto 8192, quatro threads, saída limitada a 1400 tokens. Sem repetição de respostas parciais, download automático ou fallback pago. Memórias e documentos não são apagados na troca. Cada resposta concluída registra o **modelo efetivamente capturado para aquela geração**; mensagens antigas não recebem um rótulo retrospectivo.

O diagnóstico diferencia servidor ausente, falha de comunicação, modelo ausente, instalado sem teste, texto verificado e memória insuficiente. Um teste bem-sucedido é vinculado ao digest instalado, não apenas ao nome. A publicidade de `tools`/`vision` em `/api/show` não habilita ferramentas/visão. A ponte atual é textual com RAG; completar chamadas nativas de ferramentas/visão exige validação adicional com os pesos disponíveis. Groq e suas aprovações continuam preservados.

## Executar no Codespace do proprietário

No terminal do Codespace, depois de salvar eventuais alterações locais:

```bash
cd /workspaces/nexora
git switch feat/saly-smolin
git pull --ff-only
bash scripts/install.sh
bash scripts/setup-ollama.sh
```

O instalador é uma ação explícita, nunca parte do início normal. Requer Linux amd64/arm64, curl, GNU tar com zstd e `.venv/bin/python`; usa distribuição oficial CPU sem sudo. Verifica disco (17 GiB antes do conjunto, 7 GiB antes de cada peso) e RAM efetivamente livre (mínimo conservador de 6 GiB antes dos pesos). Os aproximadamente 11 GiB dos quatro modelos são estimativa, não tamanho medido. Se faltarem recursos, rede ou uma tag, interrompe e explica o motivo; não apaga arquivos, aumenta o plano ou inicia downloads simultâneos. Um Codespace de 4 GiB pode não comportar essa configuração: o script não afirmará que funciona.

Não há API paga habilitada por esta atualização. CPU/armazenamento continuam sujeitos à franquia **da conta Codespaces**, que não foi verificada; não se garante hospedagem ilimitada a custo zero. Nenhuma cobrança ou mudança de plano é autorizada pelo script.

Depois de instalar/reiniciar:

```bash
bash scripts/start-ollama.sh
SALY_SECURE_COOKIE=1 bash scripts/start.sh
```

Na SALY, abra o seletor da conversa ou Configurações → Sistema; atualize a lista, escolha um modelo instalado e pressione **Testar modelo local**. O teste produz resposta real em português, tempo e resultado privado por digest. Em uma conversa existente, a seleção se aplica a essa conversa; nas configurações/sem conversa, muda o padrão das próximas. Durante a geração, o seletor do chat fica bloqueado: termine ou interrompa antes da troca. Para manter Groq, selecione **Provedor remoto configurado**. A autorização de envio remoto permanece necessária para Groq, não para Ollama.

`.venv/bin/python scripts/probe-ollama.py`: gera uma resposta textual nativa por modelo, sequencialmente, e registra `.tools/ollama/probe.json` (privado/ignorado pelo Git); não altera a base de testes da aplicação nem habilita ferramentas. Nunca encaminhe 11434 publicamente: `.devcontainer/devcontainer.json` ignora autoencaminhamento dessa porta; somente 8000 mantém a configuração existente. Logs, PID, chave interna do runtime e pesos ficam em `.tools/ollama/`, ignorados pelo Git. O conteúdo precisa de backup privado antes de excluir/recriar o Codespace.

Uma PWA Android continua usando o backend do Codespace. O Ollama no servidor não instala um modelo no celular nem garante conversa offline quando o servidor/rede estiver indisponível.

## Núcleo e identidade

Origem preservada: esfera/shaders/toros/partículas de `f03426b:frontend/src/Core.tsx`, recuperados seletivamente em `0dff8a9` e documentados em `docs/SALY_FLUID_CORE_RECOVERY.md`. A função `fluid` original permanece. Esta atualização adiciona uma deformação radial dependente da posição e da fase, com contração principal e secundária; não substitui o movimento original por escala global. Caústicas, fresnel, fibras ramificadas internas e fluxo luminoso permanecem tridimensionais. Verde esmeralda recebe acentos sutis de lima.

Configurações → Sistema → Pulsação do núcleo permite intensidade e velocidade (persistência neste dispositivo). Bloom via `UnrealBloomPass` somente em qualidade alta com `EXT_color_buffer_float`, preservando transparência; não é carregado como pipeline em qualidade baixa/movimento reduzido. Há descarte de materiais/render targets, pausa por invisibilidade e fallback existente. O microfone/PCM continuam usando os sinais reais existentes; fala do navegador sem PCM usa somente o estado de evento, sem inventar amplitude. Batimento de repouso é efeito visual, não medição biológica ou prova de consciência.

## ZIP: uso, limites e privacidade

Envie pelo upload existente do Centro Smolin. Para ZIPs já cadastrados com o extrator anterior (apenas lista de nomes), pressione **Reprocessar**; os originais não são substituídos nem reindexados automaticamente no início. Cada entrada recebe caminho, índice estável, tamanho, páginas e estado; diretórios vazios também são preservados. Expanda **Arquivos e pastas do ZIP** no cartão. **Abrir** preserva bytes do PDF/imagem/texto em resposta privada; HTML e formatos ativos são baixados com `sandbox`/`nosniff`, nunca executados como página da SALY. **Baixar original** continua retornando o ZIP integral, inalterado. Executáveis só ficam dentro do original e não recebem download individual. Não há interpretação de código, execução de macros ou requisições de conteúdo externo.

PDF, TXT, Markdown, CSV, JSON, HTML, DOCX, ODT, apresentações, planilhas e EPUB reutilizam os extratores reais existentes. Imagens reutilizam Tesseract quando disponível, com indicação de OCR; não há descrição visual generativa garantida. Arquivos não suportados são listados honestamente; PDF corrompido não invalida os irmãos válidos. ZIPs dentro de ZIP são listados sem expansão recursiva. Conteúdo não vira memória pessoal nem instrução de sistema. A importação ZIP desabilita embeddings remotos automáticos mesmo quando uma autorização anterior existir. Envio de trechos ao modelo remoto só ocorre depois em conversa autorizada.

A validação ocorre antes de ler os membros: diretório central limitado antes da alocação, ZipSlip, caminhos absolutos Windows/POSIX, segmentos ambíguos, duplicatas sem diferenciar maiúsculas, links/arquivos especiais, criptografia, compressão e expansão. Extração interna usa nomes numéricos em temporário privado **fora do checkout**, um membro por vez, sem usar caminhos enviados como destinos. O processo extrator já limita CPU a 90 s, memória virtual a 1 GiB e duração a 180 s. Limites padrão:

| Configuração | Padrão | Teto implementado |
|---|---|---|
| `SALY_ZIP_MAX_ENTRIES` | 200 | 1000 |
| `SALY_ZIP_MAX_EXPANDED_MB` | 128 MiB | 256 MiB |
| `SALY_ZIP_MAX_FILE_MB` | 32 MiB | 64 MiB |
| `SALY_ZIP_MAX_DEPTH` | 8 | 16 |
| Relação descompactado/compactado | 100:1 | fixa |
| Texto agregado | 2 milhões de caracteres | fixo |
| `SALY_MAX_PAGES` | 2000 páginas/seções | configuração existente |
| Diretório central | 8192 bytes × limite de entradas | ZIP64/multipartes não suportados |

O limite existente por upload continua 64 MiB por padrão (`SALY_SMOLIN_MAX_UPLOAD_MB`); o acervo tem orçamento lógico de 200 MiB (`SALY_MAX_TOTAL_MB`) e 50 documentos por padrão. ZIP conta como um documento contêiner; seus índices reservam tamanho estimado de texto/chunks antes da escrita e participam da quota das novas transferências. Isso não mede SQLite, backups e filesystem byte a byte. Uma reserva conservadora de processamento que falhou pode permanecer até reprocessar/excluir o documento; nenhuma capacidade é aumentada automaticamente.

Há uma fase de extração isolada antes da indexação incremental por página, com checkpoints existentes, pausa/retomada e progresso do job. A árvore detalhada aparece após a extração; não existe barra de progresso de cada parser interno durante essa fase. Trechos recuperados têm `archive_path`, `source_page`, `entry_index`, título/autor quando presentes e URL privada correta; não se concatena o ZIP inteiro no prompt. A exclusão do contêiner remove original, páginas, manifesto, chunks, vetores e referências derivadas pelo fluxo existente. Não se modifica um ZIP para remover apenas um membro: para isso, reenvie uma cópia revisada.

## Verificação e arquivos

Resultado da regressão completa: **175 testes Python passaram, 1 PostgreSQL ignorado por falta de serviço**, e **21 testes Vitest passaram**. Build de produção concluído; aviso existente de tamanho do bundle Three/PDF permanece. Ruff e validação sintática dos scripts passaram.

Testes automatizados do backend incluem mudança na mesma conversa sem perder histórico, metadados por resposta, geração NDJSON controlada, liberação do modelo, ausência de fallback, catálogo/servidor indisponível e ZIP com PDF, DOCX, JSON/HTML, imagem OCR real, arquivo corrompido, caminhos maliciosos, symlink, criptografia, bomba, diretório central, quota, preview e exclusão. Transporte controlado não é apresentado como inferência nativa.

Validação no Chromium com banco descartável: `scripts/browser_fluid_recovery.py` (39.617 pixels alterados entre quadros reais, microfone de teste real, redução de movimento estável, celular e quatro áreas), e `scripts/browser_integrated_update.py` (seleção persistente, árvore ZIP, bytes privados, controle persistente, bloom WebGL ativo, sem erros JavaScript). Capturas de execução: `/tmp/saly-restored-fluid-desktop.png`, `/tmp/saly-restored-fluid-mobile.png`, `/tmp/saly-integrated-high.png`; não são arquivos pessoais nem prova em aparelho Android físico.

```bash
.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
.venv/bin/python scripts/browser_fluid_recovery.py
.venv/bin/python scripts/browser_integrated_update.py
```

Arquivos principais: `backend/llm/ollama.py`, `backend/main.py`, `backend/memory.py`, `backend/smolin/{archives,extract,service,catalog,uploads}.py`; `frontend/src/{LocalModels,ArchiveTree,CoreMotion,CoreBloom,BotanicalCanvas,Core,Panels,Smolin,main}.tsx`, `frontend/src/botanical.css`; scripts `setup-ollama.sh`, `start-ollama.sh`, `probe-ollama.py`, `browser_integrated_update.py`; `.devcontainer/devcontainer.json`; testes `test_integrated_update.py` e atualização da expectativa antiga de ZIP em `test_smolin_files.py`. Nenhuma dependência frontend nova foi adicionada.

A entrega completa de quatro modelos funcionais com ferramentas/visão **permanece bloqueada**. Resolver a rede e testar os pesos no Codespace real é necessário antes de afirmar disponibilidade de inferência, capacidades por modelo ou desempenho de geração.
