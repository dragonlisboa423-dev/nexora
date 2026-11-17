# Testes da especificação 2026.11.15

## Base e primeira correção

Na base `64812e5`, `bash scripts/test.sh` passou: **97 Python, 1 PostgreSQL pulado por DSN ausente, 6 Vitest e build TypeScript/Vite**. O FFmpeg local informa versão 7.1.5 e licença GPLv2-or-later; isso verifica a ferramenta disponível, não um editor de vídeo implementado.

Após corrigir o importador, os quatro testes selecionados de importação passaram. Cobrem erros por campo sem ecoar conteúdo privado, prévia sem escrita, exportação/importação compatíveis, distinção do Core, confirmação, backup 0600, uso único e bloqueio de política não revisada. Ruff e build passaram. Nenhum teste chamou um modelo remoto ou serviço oneroso.

Comandos executados:

```bash
bash scripts/test.sh
.venv/bin/python -m pytest backend/tests/test_api.py -q -k 'import or core_json'
.venv/bin/ruff check backend
npm --prefix frontend run build
```

Os testes TestClient foram executados fora do sandbox pela limitação já observada de comunicação entre threads. Evidências de fases posteriores serão acrescentadas após execução efetiva; uma interface ou mock não contará como provedor comprovado.

## Fase 1 · offline e sincronização

**105 testes Python passaram, 1 PostgreSQL foi pulado por DSN ausente; 9 Vitest e build passaram.** Novos casos verificam reenvio sem duplicação, conflito por edição de outro dispositivo, tombstone sem recriação, confirmação, fuso, rollback de domínio/changelog/recibo e proteção de rotas.

`scripts/browser_offline.py` passou em Chromium real: IndexedDB criptografado opt-in, download de original com bytes corretos sem rede, recarregamento e senha incorreta/correta, conflito entre dois clientes autenticados, criação offline/reenvio idempotente, propagação de exclusões, restauração validada com fila pausada e layout móvel. A primeira tentativa encontrou uma corrida ao restabelecer a rede antes de concluir a gravação local; a retomada foi corrigida e o fluxo completo passou. `scripts/browser_smoke.py` também passou, preservando os fluxos anteriores, sem erros de página. Nenhum provedor remoto foi chamado.

O teste de navegador não comprova instalação física Android, armazenamento imune à limpeza do aparelho ou recursos não incluídos no cofre. O teste PostgreSQL permanece explicitamente não executado nesta rodada.

## Fase 2 · voz independente e presença

Dois testes de API de voz passaram com eSpeak NG real instalado em área do usuário. Build TypeScript/Vite passou. `scripts/browser_voice.py` passou: download de WAV real, `AudioContext`, pausa/retomada/parada, seleção persistente e núcleo dirigido pela amplitude PCM. Houve somente transporte de linguagem controlado para testar o botão Ouvir; a síntese foi real e nenhuma API de LLM foi chamada. A forma de onda desapareceu na pausa/parada; não houve erros de página.

A execução inicial dos testes ficou bloqueada por falha de aprovação automática por limite de uso, sem conclusão sobre segurança; após a retomada, a aprovação ocorreu e os testes foram executados. Nenhuma compra de créditos ou serviço foi realizada. Voz neural natural/exclusiva, Kokoro/Piper e dispositivo físico continuam não certificados; ver `SALY_VOICE_PROVIDERS.md`.

## Fase 3 · agenda e alarmes

Em 2026-11-16, `bash scripts/test.sh` passou: **114 Python, 1 PostgreSQL pulado por DSN ausente, 9 Vitest e build**. Ruff passou. Os sete testes de planejamento cobrem recorrência/DST, conflitos, revisões, aprovação, dois alarmes associados reagendados, deduplicação, claim/adiamento/conclusão e reinício em processos separados. `browser_planning.py` passou com agendador real observado, Notification solicitado, recarga sem repetição e layout móvel. `browser_smoke.py` passou preservando os fluxos anteriores, sem erros de página. Nenhum provedor remoto foi chamado. Não foram comprovados Push, entrega física do SO, Android físico ou execução com navegador fechado.

## Fase 4 · Compras e Espaço

Seis testes novos de domínio passaram, incluindo valores em centavos, orçamento, parcelas, revisão, imagem real normalizada/privada, exclusão, alertas, esquemas de URL, importação atômica e sincronização opt-in/cascatas. Onze testes combinados de domínio/sincronização passaram. `browser_personal.py` passou com comprovante real, acesso anônimo negado, edição, gavetas, favoritos, busca, responsividade, cópia financeira autorizada, criação/recarga offline e envio ao reconectar. A primeira rodada detectou nome acessível incompleto em seletor; corrigido e reexecutado. Nenhuma API externa foi chamada.

Regressão após a fase 4: **120 testes Python passaram, 1 PostgreSQL pulado por DSN ausente, 9 Vitest e build passaram**.

## Fase 5 · Biblioteca

Três testes Python passaram: publicação imutável, restauração como rascunho, revisão concorrente, progresso/tentativas/notas persistidos, exclusão completa e recusa de código/configuração/URL/mídia cruzada. `browser_library.py` passou: autoria manual, duas páginas reais, progresso/marcador/anotação, busca/última página, revisão/publicação explícita, viewport móvel e contexto preparado sem envio. O teste identificou rótulo acessível incompleto em textarea com conteúdo; corrigido. Build passou e não houve erros de página ou chamadas remotas.

## Fase 6 · Biologia inicial

Quatro testes de Biblioteca passaram, incluindo rascunho original/idempotência/exclusão; **12 Vitest e build passaram**. `browser_biology.py` passou em Chromium móvel: quiz persistido, cálculo/gráfico logístico, DNA/RNA, distinção celular, controles digitais do microscópio e contexto autorizado do elemento preparado sem envio. Não comprova micrografias reais, calibração, revisão editorial ou previsão ecológica.

## Fase 7 · Estúdio

Oito testes Python de mídia passaram, com FFmpeg/FFprobe reais, arquivo MP4, legendas/fade, corte, duas trilhas de áudio, cancelamento em execução e histórico. O adaptador Cloudflare foi testado somente com transporte controlado, incluindo limite diário; não houve inferência externa. `browser_studio.py` passou com download/checksum e reprodução MP4 nativa (`currentTime > 0`), recarga e layout móvel. Fontes oficiais Cloudflare foram recuperadas pelo espelho do próprio fornecedor no GitHub; conta/token/termos BFL e geração real permanecem bloqueados.

## Fase 8 · integração final de 2026-11-16

**137 testes Python passaram, 1 PostgreSQL foi pulado por DSN de teste ausente; 12 Vitest, build TypeScript/Vite, Ruff e verificação de formatação passaram.** `git diff --check` passou. Os ícones foram abertos como PNG reais de 192×192 e 512×512; manifesto JSON válido. SHA-256 do prompt íntegro e da semente original permanecem os mesmos registrados na auditoria.

Fluxos reais Chromium executados com dados/bancos descartáveis, sem chamadas a provedores de IA externos:

| Script | Evidência |
|---|---|
| `browser_smoke.py` | Login único, núcleo WebGL/2D, microfone de teste, memória, Smolin, aprovação, calculadora, Core Lab, PWA/cache público e móvel preservados. Transporte do chat é controlado, não inferência real. |
| `browser_offline.py` | Criptografia, original de documento sem rede, recarga/senha, dois dispositivos, fila, exclusão e restauração com envios pausados. |
| `browser_voice.py` | WAV eSpeak real (226.836 bytes nesta execução), AudioContext, pausa/retomada/parada, seleção e amplitude do núcleo. Não comprova som físico/naturalidade. |
| `browser_planning.py` | Eventos recorrentes, vistas, alarmes vinculados, scheduler real observado, Notification solicitada, recarga sem repetição, adiamento/conclusão e móvel. |
| `browser_personal.py` | Compras/orçamento em centavos, comprovante privado, bloqueio anônimo, gavetas/links/favoritos, criação e recarga offline com envio ao reconectar, móvel. |
| `browser_library.py` | Autoria de capítulos/páginas, publicação explícita, progresso/marcador/nota, pesquisa/última página, contexto preparado sem envio e móvel. |
| `browser_biology.py` | Atividades reais de quiz, DNA/RNA, tipos celulares, cálculo/gráfico logístico e controles digitais do microscópio, sem alegar micrografia/calibração. |
| `browser_studio.py` | Imagem privada/rotação, FFmpeg, legenda/fade, checksum do download, reprodução MP4 com `currentTime > 0`, histórico e móvel. |
| `browser_books_offline.py` | Livro/imagem escolhidos, checksum/Blob offline, agenda/alarmes para consulta, progresso/notas, conflito explícito, reenvio sem duplicação, exclusão remota e probes reais de PCM/IndexedDB/cache. |

Todos encerraram sem erros de página. A suíte também inclui teste de cancelamento de FFmpeg enquanto executava, duas faixas reais, permissão pessoal do agente/revogação de contexto, limite de mídia e notas idempotentes. Testar URL de ferramenta e contrato Cloudflare com transporte controlado **não certifica a inferência remota atual**.

Comandos reproduzíveis, após instalar dependências de navegador e motores nativos apropriados:

```bash
bash scripts/test.sh
.venv/bin/ruff check backend
.venv/bin/python scripts/browser_smoke.py
.venv/bin/python scripts/browser_offline.py
.venv/bin/python scripts/browser_voice.py
.venv/bin/python scripts/browser_planning.py
.venv/bin/python scripts/browser_personal.py
.venv/bin/python scripts/browser_library.py
.venv/bin/python scripts/browser_biology.py
.venv/bin/python scripts/browser_studio.py
.venv/bin/python scripts/browser_books_offline.py
```

Avisos observados: depreciação do uso de httpx pelo TestClient Starlette e chunk Three.js acima de 500 kB (842,42 kB, gzip 223,68 kB). Three/núcleo e páginas novas são carregados sob demanda; não removemos a experiência visual para silenciar o aviso. Não foram certificados benchmark no Android físico, build APK/Docker atualizado ou operação permanente da hospedagem. PostgreSQL/pgvector real permanece não executado nesta rodada; a configuração de CI existente prevê banco descartável, mas seu resultado remoto não foi presumido.

Bloqueios de aceitação preservados: geração externa de imagem, edição generativa, vídeo generativo, voz neural natural/exclusiva, inferência local, encoder semântico/OCR, Web Push/alarme nativo e revisão científica da edição. Consulte `SALY_IMPLEMENTATION_STATUS.md` para o alcance e instruções atuais, sem confundir todas as fases implementadas parcialmente com todos os critérios finais certificados.

Na revisão final do cofre, o contador e a prévia da fila restaurada passaram a incluir progresso e notas de livros. `browser_books_offline.py` foi reexecutado com aborto controlado de uma transação IndexedDB: o texto digitado permaneceu disponível para nova tentativa. O backup criptografado com operações de livro foi restaurado; a prévia mostrou as notas, o envio permaneceu pausado e só continuou após autorização explícita. O fluxo completo passou sem erros de página. Isso testa tratamento de falha por injeção controlada, não esgotamento físico do disco. Build passou novamente; os fluxos anteriores de cofre e compras também foram reexecutados após ajustar a propagação de erros de gravação.

## Atualização focada · arquivos Smolin e PDF original

A suíte Python passou com **148 testes e 1 PostgreSQL pulado** nesta atualização. Foram adicionados onze testes de formatos/downloads/Range/blocos/limites, rollback atômico, extração Office/EPUB, OCR real, MP4/MP3 e posição de leitura. A extração respeita os limites existentes; o arquivo original permanece independente. `browser_smoke.py`, `browser_offline.py` e `browser_smolin_files.py` passaram sem erros de página. Este último confirmou canvas com diagrama original, texto selecionável, páginas duplas/simples, posição persistida, checksum, binário grande em blocos e reprodução MP3/MP4 com busca no OCR de vídeo.

O modelo de transcrição local está bloqueado pelo CONNECT 403 no host oficial; não foi instalado nem certificado. Seu estado indisponível/503 foi testado sem criar texto falso. Android PWA permanece preparado, sem teste físico/APK. Detalhes e configuração estão em `SMOLIN_FILES_AND_PDF.md`.

Também passaram **15 testes Vitest**, build TypeScript/Vite, Ruff, formatação dos arquivos frontend alterados, sintaxe do instalador opcional e `git diff --check`. Nenhuma API de IA externa foi consumida nesta atualização.

## Evolução da biblioteca, mapa e conversa por voz

Base `d65bdbb`; especificação de biblioteca/voz recebida em 16/11/2026 (America/Sao_Paulo), lida integralmente antes de alterar arquivos. Diagnóstico, resultados por fase, limites e comandos em [`SALY_LIBRARY_VOICE_EVOLUTION.md`](SALY_LIBRARY_VOICE_EVOLUTION.md).

**156 testes Python passaram, 1 PostgreSQL foi pulado por ausência de DSN; 17 testes Vitest e build TypeScript/Vite passaram.** Ruff, formatação dos arquivos alterados e `git diff --check` passaram. Oito novos testes Python verificam EPUB/spine/metadados, scripts não executados, retomada de blocos após reabrir banco, checkpoint sem repetir extração, pausa/retomada, associação LSA sem palavra literal e filtro por livro, fontes entre documentos/exclusão, OCR real de PDF e snapshot privado do histórico. Dois novos testes Vitest cobrem ativação por nome e expiração da janela.

Chromium executou `browser_intelligent_library.py`, `browser_smolin_files.py`, `browser_voice.py`, `browser_smoke.py` e `browser_offline.py`, todos sem erros de página. O teste novo verificou três arquivos importados, ordem real de capítulos do EPUB e posição após recarga, termos/fontes entre livros, retomada com rejeição de arquivo divergente e download de checksum idêntico, pausa de parser real e retomada pela interface, voz por nome/pergunta consecutiva/desligamento/recusa de microfone e histórico escolhido cifrado no IndexedDB, recarregado e consultado offline em viewport móvel.

Reconhecimento de voz e chat do teste são transportes controlados; resposta WAV/PCM e eSpeak são reais. Isso não certifica ASR físico, inferência Groq, timbre natural ou Android físico. A fixture do histórico no navegador é controlada; API real de snapshot privado/limites é testada no backend, e criptografia/recarga offline são reais. OCR do PDF usa Poppler/Tesseract reais em inglês. A LSA aprende associações do acervo, é limitada a mil trechos e não equivale a encoder neural ou revisão científica. Não houve chamada a provedor externo de IA, instalação de serviço pago nem alteração de credenciais.

O teste de regressão antigo buscava imediatamente após confirmação do upload, antes da indexação assíncrona. Passou a esperar `status=ready` real antes da consulta. Foi preservado o medidor manual de áudio sem SpeechRecognition: só o modo de conversa automática é desativado quando não há transcritor. Limitações finais: voz neural natural/exclusiva, Whisper efetivamente instalado, avaliação factual/RAG de produção, escala acima da cobertura local, APK e Android físico permanecem sem certificação.
