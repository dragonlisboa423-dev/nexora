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
