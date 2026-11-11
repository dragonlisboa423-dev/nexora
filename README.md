# SALY Intelligence · Centro Smolin

Assistente pessoal de **proprietária única**, com memória global persistente, documentos privados, núcleo líquido bioluminescente e agente com ferramentas e aprovações. React/TypeScript/Vite/Three.js no frontend; FastAPI e SQLAlchemy no backend. PostgreSQL/pgvector para implantação; SQLite para desenvolvimento sem serviços externos.

Não existe cadastro público, seleção de contas ou memória por usuário. Um único modelo generativo remoto é configurado no servidor; **não há geração local nem resposta fictícia quando o provedor está indisponível**.

A aplicação e suas ferramentas locais foram implementadas e testadas. Inferência com um provedor real, qualidade de embeddings reais e hospedagem Supabase ainda dependem de credenciais/serviços que não foram fornecidos. Veja [validação](docs/validation.md) e o [relatório técnico](docs/delivery.md); isso não é uma afirmação de que todos os critérios finais já foram atendidos.

## Iniciar no Codespaces

Abra o terminal do Codespaces e use o checkout existente:

```bash
cd /workspaces/nexora
git fetch origin
git switch feat/saly-smolin
git pull --ff-only
bash scripts/install.sh
```

No ambiente Codex o checkout fica em `/workspace/nexora`; os scripts encontram a raiz pelo próprio caminho. **Não é necessário criar worktree.**

Python 3.12 e Node.js 24 são as versões usadas nos testes. O instalador preserva `.venv` incompatível ou sem pip como `.venv.previous.*`. Usa uv quando disponível para criar um ambiente com pip, inclusive em sistemas sem `ensurepip`. Se não houver Python/pip/uv utilizáveis, ele informa a dependência `python3.12-venv`; não apaga arquivos nem desativa TLS.

Na primeira instalação, copie a configuração sem sobrescrever um `.env` existente:

```bash
cp -n .env.example .env
chmod 600 .env
```

Edite `.env` no servidor. Defina a chave e o modelo do provedor em campos privados; não cole chaves em chats, documentos ou código. Configure o desbloqueio privado da proprietária pelo terminal:

```bash
.venv/bin/python -m backend.manage owner
SALY_SECURE_COOKIE=1 bash scripts/start.sh
```

O comando `owner` pede uma senha de pelo menos 12 caracteres de forma oculta. Não é cadastro web. Abra a aba **Portas**, encaminhe **8000** como **Privada** e use **Abrir no navegador**. A página pede somente a senha privada.

Para HTTP em computador local, use `SALY_SECURE_COOKIE=0`. Em HTTPS/produção, use `1`. Não exponha uma implantação sem HTTPS e acesso privado configurado. `.env` é lido pelo backend, CLI e servidor sem substituir variáveis já injetadas no processo.

## Modelo remoto e custo

O adaptador utiliza a API OpenAI-compatible de um único provedor remoto. O candidato inicial é Groq com `llama-3.3-70b-versatile` (pesos abertos da família Meta Llama, sujeito à licença e à disponibilidade do provedor). A tag é **configurável**, e o backend consulta `/models` para verificar sua disponibilidade; não troca de modelo silenciosamente.

```dotenv
SALY_LLM_BASE_URL=https://api.groq.com/openai/v1
SALY_MODEL=llama-3.3-70b-versatile
```

Configure `SALY_LLM_API_KEY` de forma privada. O código não cria conta, não ativa faturamento, não cadastra cartão e não contrata um plano. Confira [modelos](https://console.groq.com/docs/models) e [limites](https://console.groq.com/docs/rate-limits) atuais em sua conta antes de usar. A consulta à documentação oficial foi bloqueada com HTTP 403 neste ambiente; não foi possível confirmar quotas gratuitas atuais nem uma resposta real. Não há promessa de serviço ilimitado ou gratuito permanente.

Antes de enviar o primeiro chat, a interface pede autorização para transmitir mensagens e contexto permitido ao provedor. Essa autorização pode ser revogada em **Configurações → Privacidade**. Voz do navegador pode usar outros serviços do próprio navegador, conforme seu suporte.

Streaming, cancelamento e erros são reais. Há limites de contexto/saída, máximo de etapas do agente, limite de solicitações e backoff para 429/502/503 antes do primeiro token. Uma resposta parcial nunca é repetida automaticamente ou salva como concluída. A disponibilidade indicada exige consulta bem-sucedida ao provedor; ter uma chave configurada não é prova de inferência validada.

## Memória definitiva

Todas as conversas da proprietária consultam a mesma memória. Categorias são organizacionais: informações, preferências, projetos, decisões, atividades, instruções e temporárias. O painel permite criar, pesquisar, editar, marcar confiança/contestação, autorizar/desativar uso, arquivar, relacionar, versionar, restaurar, consolidar com aprovação, importar/exportar e excluir.

A recuperação filtra memórias contestadas, arquivadas, desativadas e expiradas. Combina correspondência textual, importância e recência; busca semântica adicional depende do encoder configurado. Editar uma memória invalida o contexto anterior. Excluir remove seus vetores, versões e relações, retira respostas derivadas identificadas e invalida aprovações pendentes/contexto histórico para que índices ou prompts antigos não a recuperem automaticamente. Backups anteriores são cópias independentes e não são apagados por essa ação.

Não há treinamento de pesos após conversas. Uma ferramenta do agente pode propor gravar uma memória, mas a gravação exige a aprovação da proprietária; não se retêm automaticamente inferências sensíveis.

## Centro Smolin e acervo Smoln

`/knowledge` oferece arrastar/selecionar vários PDFs, TXT e Markdown, progresso real de transferência, fila de processamento, cancelamento, biblioteca, metadados, páginas, texto integral, busca, original privado, reprocessamento e exclusão. O nome interno **Smoln** pode ser alterado nas configurações.

- O original é preservado em `document_originals`, como binário no mesmo banco privado. Nesta versão utiliza PostgreSQL BYTEA/SQLite BLOB, **não Supabase Storage separado**. Isso simplifica backup e exclusão transacional para um acervo pessoal; observe a quota do banco antes de arquivos grandes.
- PDFs são identificados por conteúdo e validados por parser isolado em subprocesso Linux. Limites de CPU, memória, tempo, páginas, texto, tamanho e quantidade protegem o processamento. Falhas de um documento não interrompem a fila.
- Texto e metadados são preservados por página. Os trechos têm sobreposição aproximada de 12,5%, mantêm limites de página e procuram respeitar parágrafos. Tabelas complexas podem exigir revisão; não se promete reconstrução perfeita da diagramação.
- O SHA-256 identifica duplicatas. Páginas sem texto geram `ocr_required`; documentos parcialmente extraídos são `partial`. O original permanece acessível. **OCR automático ainda não está implementado**.
- Busca lexical funciona imediatamente: FTS5 no SQLite e pesquisa textual em português no PostgreSQL. O pipeline híbrido e os vetores usam pgvector quando configurados; nenhuma representação semântica fictícia é gerada.
- Fontes possuem ID real de trecho, documento, página e posição. A interface abre o original na página correspondente. Referências inventadas no formato reconhecido são marcadas como não verificadas. Isso não certifica toda afirmação factual do modelo.

Limites padrão: 10 MB/arquivo, 50 documentos, orçamento aproximado de 200 MB de acervo, 500 páginas/PDF e 2 milhões de caracteres extraídos. Ajustes estão em `.env.example`. Há também limite de corpo antes da extração e autorização antes de receber uploads anônimos. Tamanho de banco e quotas de hospedagem ainda precisam ser monitorados pelo administrador.

### Embeddings opcionais

O backend aceita um serviço HTTPS OpenAI-compatible para `/embeddings`, com encoder multilíngue leve de **384 dimensões**, ID de modelo e revisão imutável. Configure:

- `SALY_EMBEDDING_URL`
- `SALY_EMBEDDING_API_KEY`, quando necessário
- `SALY_EMBEDDING_MODEL`
- `SALY_EMBEDDING_REVISION`

A resposta precisa confirmar a revisão em `revision` ou `X-Model-Revision`. Vetores incompatíveis, não finitos ou com dimensão diferente são recusados. O fingerprint do encoder é salvo com cada vetor; índices incompatíveis não se misturam. Alterar encoder requer reprocessar o acervo e salvar/reindexar as memórias desejadas. O índice HNSW está incluído no esquema PostgreSQL.

O contrato e a recuperação foram testados com vetores controlados; **não há encoder real configurado ou hospedado pelo projeto neste ambiente**. Sem ele, a interface informa vetores indisponíveis e preserva a busca textual. Um encoder é separado do único modelo generativo principal; não se adiciona um segundo modelo conversacional.

## Agente e ferramentas

`/tools` lista esquemas, disponibilidade real e requisitos de aprovação. Ferramentas operacionais sem integração externa: cálculo por AST, consultar/propor/criar/corrigir/excluir memória, pesquisar Smolin, obter trechos, listar documentos e gerenciar lembretes.

O modelo só pode escolher ferramentas do registro tipado. Não há ferramenta de shell nem SQL arbitrário. Leituras autorizadas podem ser automáticas; gravações e exclusões ficam em `agent_approvals`, com argumentos imutáveis, expiração e consumo único. A interface mostra **NÃO EXECUTADA** até a aprovação. Falhas externas com resultado incerto não são repetidas automaticamente.

Integrações opcionais, indisponíveis quando não configuradas:

| Integração | Configuração | Capacidade |
|---|---|---|
| GitHub | `SALY_GITHUB_TOKEN`, `SALY_GITHUB_REPOSITORY` | Ler arquivos/issues do repositório autorizado, criar issue aprovada, propor diff e alterar arquivo aprovado com proteção por SHA |
| Pesquisa web | `SALY_SEARCH_API_KEY` | Adaptador Brave com URLs e descrições reais; verifique plano/quotas antes de configurar |
| Ler fonte web | `SALY_WEB_ALLOWED_DOMAINS` | HTTPS em destinos explicitamente autorizados, bloqueio de IPs privados/reservados, sem redirects e com limites |

Não se reutiliza automaticamente a autenticação de Git desta sessão como credencial da aplicação. Chaves nunca são entregues ao modelo ou ao navegador. Respostas de ferramentas/documentos/web são dados não confiáveis. Um teste adversarial força uma proposta maliciosa de exclusão e comprova que ela não ultrapassa a barreira de aprovação; isso não significa imunidade universal a prompt injection.

## Agenda, iniciativa e voz

`/agenda` cria, edita, conclui e exclui lembretes mediante aprovação. Datas são normalizadas para UTC com fuso IANA explícito, padrão `America/Sao_Paulo`; horários ambíguos/inexistentes de horário de verão são recusados. Projeto e importância são persistentes. Avisos na aplicação obedecem ativação, horário de silêncio e importância mínima. **Não há envio garantido de notificação com a aplicação fechada**, push externo ou recorrência automática.

O microfone só inicia por ação explícita. A amplitude de entrada é analisada com AnalyserNode, há pressionar-para-falar e transcrição revisável quando o navegador suporta. É opcional aguardar “Saly” após ativar o microfone; isso não é escuta oculta nem funciona com o app fechado. A transcrição pode depender do provedor do navegador.

`/voices` exibe vozes realmente disponibilizadas pelo sistema, amostra, velocidade, tonalidade, volume e configurações persistidas. Escolha uma voz feminina pt-BR entre as existentes; a API não fornece gênero padronizado. SpeechSynthesis sincroniza o núcleo por início, pausa, retomada, limites de palavras, fim e cancelamento. A amplitude da saída é uma aproximação, **não medição PCM exata**. Voz física, wake word e transcrição devem ser validados no dispositivo alvo.

## Núcleo e PWA

O núcleo usa shader procedural com deformação da superfície, iluminação interna, translucidez e simulação óptica eficiente. A máquina de estados centralizada inclui captura, transcrição, recuperação, processamento documental, ferramentas, fala, sucesso, erro e offline. Timers só controlam transições visuais de confirmação já recebida; não concluem tarefas. Operações concorrentes têm IDs próprios. Há qualidade reduzida, limite de partículas/DPR, alternativa 2D e respeito a movimento reduzido.

A PWA contém manifest, ícones originais, service worker, instalação quando suportada, aviso de atualização e página offline. **Somente shell/recursos públicos são cacheados; APIs, documentos, chaves e memória ficam fora do cache.** Sem servidor/conexão não há inferência remota nem acesso offline prometido ao banco privado. Uma atualização não é aplicada automaticamente no meio da conversa.

## Banco e implantação

Sem `SALY_DATABASE_URL`, o banco local é `data/saly-v2.sqlite3`. Use um volume privado persistente. Para uma implantação que sobreviva a recriações do servidor, configure uma conexão **PostgreSQL/Supabase exclusiva do backend**, com TLS verificado. O mesmo esquema é usado no desenvolvimento e na produção; não há tabela de usuários.

A migração em [supabase/migrations](supabase/migrations/202611110001_global_saly.sql) cria tabelas globais, pgvector, índices e RLS. Aplique-a como administrador. Nenhuma política permite acesso público/anon; a aplicação opera pelo papel servidor confiável. Não use uma chave `service_role`, DSN ou senha no frontend. O backend também inicializa o esquema idempotentemente; futuras alterações precisam de migrações versionadas adicionais.

Para um host sem terminal privado, gere localmente o hash de desbloqueio:

```bash
.venv/bin/python -m backend.manage hash-owner
```

Configure a saída como `SALY_OWNER_PASSWORD_HASH` em variável privada do servidor. Ela só inicializa o acesso se o banco ainda não tiver proprietária; não sobrescreve uma senha existente. Não coloque o hash em `VITE_*` ou no repositório. A senha em texto puro nunca é persistida.

Docker Compose opcional usa PostgreSQL/pgvector, sem motor local de linguagem:

```bash
# Defina SALY_POSTGRES_PASSWORD forte em .env, além das configurações desejadas.
docker compose up --build -d
docker compose exec saly python -m backend.manage owner
```

Volumes preservam os dados; `docker compose down -v` os destrói. A porta publicada fica em loopback. O Dockerfile foi compilado e um PostgreSQL real foi testado; isso não equivale a validar uma conta Supabase ou hospedar a aplicação publicamente.

`render.yaml` é um blueprint opcional com plano web gratuito e banco externo. Revise os limites atuais antes de usá-lo; não foi publicado, não cria banco pago e não promete disponibilidade contínua. Sistemas serverless que encerram processos após a resposta não suportam a fila atual sem um worker durável: prefira um processo ASGI/container, ou implemente essa fila antes de adotar funções efêmeras. [Mais instruções de implantação](docs/deployment.md).

## Migração da versão anterior

Se `data/saly.sqlite3` existir e não houver v2, a inicialização recusa criar um espaço vazio silenciosamente. Pare a versão anterior, faça backup e execute:

```bash
.venv/bin/python -m backend.manage migrate-legacy data/saly.sqlite3
```

O original é aberto somente para leitura e recebe um backup separado `.before-global.bak`. Senha, memória, conversas, texto documental e datas são preservados. Se houver múltiplas contas antigas, escolha explicitamente `--owner-id`; não se mesclam automaticamente dados de pessoas diferentes. A origem permanece intacta. Originais PDF nunca guardados pela versão antiga não podem ser recriados: são marcados como `legacy_text_only`, sem inventar páginas. Reimporte os PDFs originais para referências precisas.

A migração foi testada com fixture, **não executada nos dados do seu Codespaces**, que não estão neste checkout. Os ZIPs anteriores não foram importados, pois excediam o limite de transferência.

## Backup e recuperação

Backup integral SQLite (inclui originais e vetores):

```bash
.venv/bin/python -m backend.manage check
.venv/bin/python -m backend.manage backup /caminho/privado/saly-backup.sqlite3
```

Para recuperar, pare o serviço e use um diretório novo:

```bash
SALY_DATA_DIR=/caminho/novo .venv/bin/python -m backend.manage restore /caminho/privado/saly-backup.sqlite3 --confirm-stopped
```

Depois atualize `.env`. A restauração não sobrescreve bancos existentes e invalida sessões. PostgreSQL exige backup integral com `pg_dump`/restauração correspondente. A exportação JSON da interface é útil, mas não substitui esse backup: não inclui os binários ou todos os vetores. O banco não é cifrado em repouso pela aplicação; proteja o volume e suas cópias.

## Testes e desenvolvimento

```bash
bash scripts/test.sh
.venv/bin/pip install -r backend/requirements-browser.txt
.venv/bin/python scripts/browser_smoke.py
```

Para incluir o teste PostgreSQL, forneça `SALY_TEST_DATABASE_URL` de um **banco descartável**, nunca produção. Sem isso, somente esse teste é marcado como não executado. O CI prepara um PostgreSQL de teste; o workflow ainda precisa executar no GitHub após a publicação da branch.

Desenvolvimento com recarga:

```bash
.venv/bin/uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
# Em outro terminal:
npm --prefix frontend run dev
```

Documentação técnica e limites: [arquitetura](docs/architecture.md), [validação](docs/validation.md), [entrega](docs/delivery.md). Funcionalidades ainda dependentes de serviços externos não são apresentadas como validadas.
