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
