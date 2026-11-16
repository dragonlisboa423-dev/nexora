# Auditoria de implementação · especificação 2026.11.15

Base inspecionada: commit `64812e5`, branch `feat/saly-smolin`. O prompt mestre completo, 58.859 bytes, foi lido integralmente e preservado em `CODEX_INTEGRATION_PROMPT.md`, SHA-256 `91c471f8866f9735f61a2c13321a38c9aa5d8a96426e5a14c2255cb4fbe39374`. Esta auditoria sucede a etapa independente documentada em `core-phase-1.md`.

## Material encontrado

`SALY_CORE_MEMORY_v1.json` está em `backend/core/data/`, validado pelo manifesto. `README.md` e os relatórios v2/Core existem. `SALY_Core_v1/`, `saly.core.json` e o ZIP modular continuam ausentes. `docs/CODEX_INTEGRATION_PROMPT.md` passou a existir com o texto recebido nesta solicitação; seu conteúdo não foi inventado.

## Inventário inicial

| Funcionalidade | Estado na base | Evidência / limite |
|---|---|---|
| Interface cinematográfica | Implementado e comprovadamente funcional no Chromium de teste | `Core.tsx`, shaders R3F, fallback 2D, `browser_smoke.py`; sem instalação física Android. |
| Chat Groq e agente | Parcial / conexão real atual não verificada aqui | `llm/provider.py`, `agent/registry.py`; SSE, ferramentas e aprovações testados com transporte controlado. Modelo da conta e chave não são alterados. |
| Core Memory | Parcial | `core/policy.py`, manifesto, 12 regras, recuperação lexical e verificadores; pacote modular ausente. Sem treinamento de pesos. |
| Memória no servidor | Implementado e comprovadamente funcional em testes | CRUD, versões, exportação, exclusão e teste em dois processos. Retenção/sensibilidade/sincronização ainda precisam evoluir. |
| Importador JSON | Parcial, defeito reproduzível | Frontend enviava apenas `data.memories`; Core JSON não possui esse campo. API emitia erro de validação que o cliente mostrava como 422 genérico. Ainda é necessário distinguir outros erros por campos. |
| Smolin | Parcial | Original privado, parser isolado, páginas, FTS e citações; OCR ausente e encoder real não conectado neste ambiente. |
| Sessão única e segurança | Implementado e comprovadamente funcional nos casos testados | `security.py`, CSRF/origem, cookies, limites e testes anônimos. Não equivale a segurança universal. |
| PWA | Parcial | Manifesto/ícones/service worker versionado e cache público; offline só abria página de indisponibilidade. |
| IndexedDB e sincronização | Ausente | Nenhuma réplica privada local ou fila de conflitos na base. |
| Vozes do navegador e microfone | Parcial | Seleção, prévia, eventos reais e captura por botão; dispositivo de teste. Sem motor TTS próprio instalado. |
| Kokoro/Piper | Bloqueado por dependência não verificada | Pesos, licença dos artefatos, compatibilidade e áudio real ainda precisam ser comprovados. |
| Agenda | Parcial | Lembretes globais com aprovação e fuso. Sem calendário completo, recorrência e agendador persistente. |
| Alarmes | Ausente como sistema dedicado | Avisos somente com aplicação aberta; sem Web Push configurado ou alarme nativo. |
| Compras / orçamento / anexos | Ausente | Nenhuma entidade ou aba na base. |
| Espaço / gavetas | Ausente | Nenhum CRUD ou validação de links na base. |
| Biblioteca / editor / Biologia | Ausente | Sem catálogo, páginas, autoria manual, simulações ou progresso na base. |
| Imagens por IA | Bloqueado por dependência | Nenhum provedor implementado/conectado, conta/credenciais/quota gratuita não fornecidas. |
| Vídeo generativo | Bloqueado por dependência | Sem motor, GPU ou quota gratuita comprovada. |
| Edição de vídeo | Ausente no app; ferramenta local disponível | FFmpeg/ffprobe 7.1.5 presentes, build GPLv2-or-later. Ainda sem pipeline da SALY. |
| Laboratório | Parcial | 6 verificações locais e 16 casos do modelo inconclusivos; exportação real. |

## Dependências e infraestrutura

React 19.1, TypeScript 5.8, Vite 8.3, Three.js/R3F, FastAPI/Pydantic e SQLAlchemy são preservados. SQLite mantém desenvolvimento sem serviço externo; PostgreSQL/pgvector são suportados. Não há chave de aplicação ou GPU comprovada neste ambiente. FFmpeg local pode permitir montagem sem API. Isso não confirma disponibilidade do FFmpeg no Codespaces da proprietária ou na imagem Docker atual.

Nenhuma chave foi exposta ou alterada. Novos testes não podem consumir serviços onerosos. Configuração local, existência de biblioteca e resultado com mock não serão tratados como prova de voz/imagem/vídeo generativos reais.

## Plano incremental

0. Registrar esta base, regressão e custos; preservar o prompt recebido.
1. Corrigir importação/422 e revisão administrativa do Core; acrescentar base privada offline, migrações, sincronização idempotente e conflitos; testar permissões e reinício.
2. Contratos de voz, capacidades reais e integração de áudio; instalar motor apenas se licença/compatibilidade/download forem verificáveis. Recursos bloqueados permanecem identificados.
3. Agenda/recorrência e alarmes persistentes; separar notificações na aba aberta, push e alarmes nativos.
4. Compras manuais com centavos/anexos privados e Espaço com links seguros.
5. Motor/editor manual da Biblioteca, revisão/publicação e progresso.
6. Edição inicial de Biologia como rascunho e experiências didáticas verificáveis.
7. Estúdio: contratos de geração sujeitos a quota gratuita, edição local real com FFmpeg quando disponível, arquivos validados e cancelamento.
8. Testes integrados, acessibilidade, móvel, documentação e matriz final de recursos demonstrados/pendentes.

Cada etapa deve manter o aplicativo utilizável e receber commit próprio. Migrações serão aditivas; não haverá reset de banco, exclusão do histórico Git, mudança silenciosa de modelo ou ativação de faturamento. O alcance final será documentado pelo comportamento efetivamente executado, sem presumir que todas as fases passaram seus critérios.

## Progresso comprovado · fase 1

Importador/422 e revisão administrativa do Core foram corrigidos no commit `359ec4a`. A base offline agora dispõe de cofre IndexedDB opcional criptografado, leitura/edição de memórias e lembretes, documentos guardados seletivamente, configurações para consulta, fila idempotente e conflitos/exclusões com revisão. Os critérios relativos a estes tipos foram exercitados em Chromium com rede desligada e dois dispositivos lógicos. A consulta semântica, o modelo local e as futuras abas continuam fora desse alcance.

As consultas oficiais ao modelo Cloudflare e à ficha Kokoro foram tentadas com TLS/proxy herdados. O sandbox não alcançava o proxy; a tentativa fora dele recebeu **CONNECT 403 da política de rede** para `developers.cloudflare.com` e `huggingface.co`. Não se concluiu que o serviço ou a licença sejam inválidos; o bloqueio é de acesso neste ambiente. Pesos não foram baixados, preço/franquia não foram certificados e nenhum serviço de geração foi chamado.

## Progresso comprovado · fase 2 parcial

Motor eSpeak NG real, pt-BR com variante feminina `f3`, foi verificado por pacotes oficiais/licenças e integrado como síntese independente. WAV, reprodução, pausa/parada, seleção e amplitude do núcleo passaram em API/Chromium. A voz é artificial por formantes: não satisfaz ainda o requisito de naturalidade neural. Kokoro/Piper, instalação no aparelho e áudio físico permanecem pendentes. Microfone e vozes do navegador foram preservados; não existe escuta permanente disfarçada.

## Progresso comprovado · fase 3

Agenda com eventos/recorrência, prévia de conflitos e alarmes persistentes foi exercitada por API, reinício em processos separados e Chromium. Suíte: 114 Python, 1 PostgreSQL pulado, 9 Vitest e build; regressão visual passou. Avisos dependem de backend/interface ativos; Push e alarme nativo permanecem ausentes. Consulte `SALY_ALARMS_AND_AGENDA.md`.

## Progresso comprovado · fase 4

Compras manuais/orçamento em centavos, comprovantes normalizados privados e gavetas/links seguros foram exercitados por API/Chromium, incluindo edição offline opt-in e sincronização. Binários de comprovantes e novos alarmes não são replicados no cofre; orçamento local é consulta. Consulte `SALY_PURCHASES.md` e `SALY_SPACE_DRAWERS.md`.

## Progresso comprovado · fase 5

Editor manual e leitor estruturado foram testados com versões publicadas imutáveis, rascunhos/restauração, notas, progresso, páginas duplas/únicas e contexto de tutoria apenas preparado. Conteúdo científico, mídia audiovisual e cópia de livros offline são extensões posteriores; ver `SALY_INTERACTIVE_LIBRARY.md`.

## Progresso comprovado · fase 6

Rascunho original de Biologia com nove páginas e atividades determinísticas foi exercitado por Python, Vitest e Chromium móvel. O microscópio é um esquema explícito sem calibração física; capítulos futuros e revisão editorial continuam identificados. Nenhuma obra externa foi importada.

## Progresso comprovado · fase 7 parcial

Edição local de imagem e montagem FFmpeg com clipes, imagens, duas trilhas, legendas, transições, cancelamento e MP4 verificável passaram por testes reais. Conector Cloudflare segue desativado: contrato oficial recuperado no GitHub, mas conta/credencial/termos e geração externa não comprovados. Vídeo generativo continua não configurado. Veja `SALY_MEDIA_PROVIDERS.md` e `SALY_FREE_TIER_LIMITS.md`.
