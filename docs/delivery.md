# Entrega técnica · SALY v2 · 11/11/2026

## Diagnóstico

A `main` do repositório continha apenas o README inicial. A implementação anterior estava na branch publicada `feat/saly-intelligence`, commit `f9d7859`. Ela tinha React/R3F, FastAPI, SQLite por usuário, cadastro inicial e dependência de um motor local. A nova branch `feat/saly-smolin` parte desse histórico, preservando-o; não houve reset, force-push ou remoção de dados fornecidos pela proprietária.

Os ZIPs antigos não foram importados (transferência acima do limite). Não há banco privado do Codespaces neste checkout, portanto não foi executada migração sobre seus dados reais. A migração está pronta e foi testada em banco de fixture, preservando fonte, hash de senha, conteúdo e datas.

## Mudanças reais

1. Registro web, usuário selecionável e separação por conta removidos. Acesso singleton preparado por CLI privada ou hash inicial seguro no servidor; a interface tem somente desbloqueio.
2. Um banco global para todas as conversas, memórias, documentos, agenda e auditoria. SQLAlchemy opera SQLite local e PostgreSQL/pgvector. RLS/índices incluídos na migração; leitura por papel SQL de teste não autorizado foi bloqueada de fato.
3. Adaptador remoto OpenAI-compatible, modelo único configurável, SSE para o provedor e NDJSON para a interface, cancelamento, limites, controle de 429 e ausência de fallback fictício. Nenhum motor local é instalado pela configuração atual.
4. Registro tipado do agente, ferramentas locais reais, resultados auditáveis, aprovações de uso único, revisão de argumentos, expiração e recusa de operações que mudaram desde a proposta. GitHub tem proteção de diff/SHA; integrações não configuradas ficam indisponíveis.
5. Centro Smolin preserva original privado, texto integral e metadados por página. Upload múltiplo, bytes transferidos, jobs, cancelamento, duplicatas, limites de subprocesso, páginas sem texto, reprocessamento, referências e exclusão foram implementados.
6. Encoder opcional de 384 dimensões com revisão imutável confirmada, índice pgvector/HNSW e fallback lexical declarado. Contrato/híbrido foram exercitados com vetores controlados; não há encoder real configurado ou benchmark semântico realizado.
7. Memória com importância, origem, validade, uso autorizado, categorias, versões, relações, import/export e consolidação. Exclusão remove vetores/versões, limpa respostas derivadas identificadas e invalida contexto antigo/aprovações para impedir recuperação automática por índices antigos.
8. Agenda persistente, fusos IANA/UTC, projeto, importância, edição/exclusão/conclusão aprovadas e avisos enquanto o app está aberto, com silêncio configurável. Salvar não é entregar push; não há agendador externo ou recorrência automática.
9. Núcleo líquido procedural deformável, estado operacional centralizado, reações de entrada real, eventos de saída vocal, qualidade/fallback e movimento reduzido. Microfone continua condicionado à ação explícita. A opção “aguardar Saly” é limitada à sessão de captura ativa em navegador compatível.
10. Markdown sem HTML bruto, blocos de código, cópia, nova geração, histórico pesquisável e referências contextuais. Imagens remotas não são carregadas automaticamente.
11. Manifest, ícones próprios, service worker, atualização controlada e página offline. APIs/documentos não entram no cache público.
12. Instalador recupera Python 3.12/venv sem apagar o anterior. Configuração `.env` é carregada pela API/CLI/launcher. Docker, Compose PostgreSQL, devcontainer, workflow de testes e blueprint opcional foram atualizados.

## Arquivos principais

| Área | Arquivos |
|---|---|
| API e execução | `backend/main.py`, `backend/serve.py` |
| Banco e acesso | `backend/storage.py`, `backend/security.py`, `backend/manage.py` |
| Memória | `backend/services.py`, `backend/memory.py` |
| Modelo | `backend/llm/provider.py` |
| Agente e integrações | `backend/agent/registry.py`, `backend/integrations.py`, calculadora reaproveitada |
| Smolin | `backend/smolin/service.py`, `backend/smolin/extract.py` |
| Migração PostgreSQL | `supabase/migrations/202611110001_global_saly.sql` |
| Interface | `frontend/src/main.tsx`, `Core.tsx`, `Panels.tsx`, `Smolin.tsx`, `AgentPanels.tsx`, `audio.ts`, `operations.ts`, CSS |
| PWA | `frontend/src/pwa.tsx`, `frontend/public`, `frontend/vite.config.ts` |
| Testes | `backend/tests`, `frontend/src/operations.test.ts`, `scripts/browser_smoke.py` |
| Operação | `.env.example`, `scripts`, `.devcontainer`, `Dockerfile`, `compose.yaml`, `render.yaml`, `.github/workflows/tests.yml` |

## Migrações

Esquema v2 inicializado em bancos temporários de teste e banco local novo. PostgreSQL real com pgvector foi utilizado para testar tipos, busca, RLS e cascata. A migração SQL correspondente é versionada e idempotente. Supabase de produção não foi acessado ou migrado; precisa de um projeto e conexão privados reais.

Para banco v1: parar a versão anterior, preservar backup e executar `python -m backend.manage migrate-legacy <arquivo>`. Se houver mais de uma conta, informar `--owner-id`; não se mesclam dados sem escolha. O original permanece intacto e uma cópia anterior à migração é criada. Caso uma migração seja interrompida, preserve os arquivos e refaça em um destino novo, sem apagar a fonte. PDFs não guardados pela versão antiga não são reconstruídos artificialmente.

## Serviços e variáveis

Obrigatórios para inferência: `SALY_LLM_BASE_URL`, `SALY_LLM_API_KEY`, `SALY_MODEL`, com um modelo realmente anunciado pelo provedor e quotas verificadas. O candidato padrão é Groq/Meta Llama; as páginas oficiais foram bloqueadas pela rede deste ambiente, por isso não se atesta a oferta gratuita atual.

Implantação persistente: `SALY_DATABASE_URL` backend-only com PostgreSQL/pgvector, TLS e permissões adequadas. O fallback de desenvolvimento usa `SALY_DATA_DIR` em volume persistente. Acesso: CLI privada ou `SALY_OWNER_PASSWORD_HASH` inicial; HTTPS usa `SALY_SECURE_COOKIE=1`.

Opcionais: encoder (`SALY_EMBEDDING_URL`, chave, modelo e revisão), GitHub (`SALY_GITHUB_TOKEN`, repositório autorizado), pesquisa Brave e destinos web autorizados. Sem esses valores, as capacidades correspondentes não fingem estar prontas. Não são solicitadas chaves em chat.

## Instalar, executar e publicar

Na raiz do checkout:

```bash
bash scripts/install.sh
cp -n .env.example .env
chmod 600 .env
# Edite .env privadamente; não substitua valores existentes sem revisar.
.venv/bin/python -m backend.manage owner
SALY_SECURE_COOKIE=1 bash scripts/start.sh
```

No Codespaces a raiz é `/workspaces/nexora`; neste ambiente Codex é `/workspace/nexora`. Encaminhe 8000 como porta privada. Para HTTP local, configure cookie Secure como 0; para produção, HTTPS e Secure=1.

A branch contém código e configuração de implantação. Publicar uma branch Git não é hospedar o site. Não foi realizado deploy público, criado projeto Supabase, ativado plano pago ou publicado snapshot desta versão em tarefa nova. `render.yaml`/Compose são pontos de partida revisáveis, com instruções em `deployment.md`. Quotas gratuitas, suspensão e retenção devem ser confirmadas no serviço escolhido.

## Testes, limitações e pendências

Resultados e distinção entre testes reais, controlados e não executados estão em `validation.md`. Build, testes da aplicação e browser foram executados; o banco vetorial foi real, mas o encoder e o modelo de linguagem foram simulados somente nos testes de contrato. Não há resposta de IA simulada na produção.

Ainda dependem de configuração/validação: geração remota real com streaming/cancelamento, qualidade de português e ferramentas do modelo escolhido, encoder multilíngue real, Supabase hospedado, quotas/custo gratuito verificados, integração GitHub/web com credenciais reais, voz e reconhecimento físicos. Ainda não implementados: OCR automático, push/agendador externo, recorrência, integração de calendário externo, backend de embeddings hospedado pelo próprio projeto, extração avançada de tabelas, OAuth da proprietária, fila distribuída/durável para funções efêmeras e avaliação factual ampla.

O teste adversarial comprova a barreira de aprovação, não a invulnerabilidade universal a prompt injection. O verificador confere fontes reconhecidas e operações confirmadas, não garante verdade universal. Dados privados exigem backup, retenção e proteção do volume.
