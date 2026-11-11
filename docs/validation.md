# Evidências de validação · 11/11/2026

A implementação v2 foi verificada no ambiente Codex, em SQLite e PostgreSQL/pgvector descartável. **Não se considera a assistente integralmente validada em produção:** modelo remoto real, encoder real, credenciais de integrações, Supabase hospedado e áudio físico continuam pendentes.

## Checks executados

| Check | Resultado observado |
|---|---|
| Instalador completo | Passou: Python 3.12, dependências fixadas, npm ci, build e esquema v2; repetição preservou o ambiente |
| TypeScript/Vite | Build passou |
| Vitest | **6 testes passaram** da máquina de estados, concorrência, cancelamento, offline e confirmação real |
| Pytest com PostgreSQL de teste habilitado | **54 testes passaram**, sem skips nessa execução |
| PostgreSQL 17 + pgvector | Banco real em Docker: busca por distância, pesquisa textual, referência de página, RLS e exclusão em cascata passaram |
| Migração SQL versionada | Executada com sucesso no PostgreSQL descartável; extensão pgvector observada: 0.8.7 |
| Segurança de acesso | Sem registro; sessão/expiração/logout, CSRF, limitação de tentativas, APIs privadas e upload anônimo bloqueados |
| Memória única | CRUD, versões, restauração, export/import, consolidação, importância/validade, persistência entre processos, invalidação de contexto e exclusão de derivados/vetores |
| Migração legada | Fixture com hash/senha, texto e datas preservados; original e backup intactos; repetição recusada |
| Documentos | PDF textual, múltiplas páginas, acentos, 25 páginas, texto de tabela simples, página vazia, parcial, corrompido, duplicado, limite de páginas, cancelamento, reprocessamento e original byte a byte |
| Fontes | Trechos apontam para documento/página reais; IDs inventados reconhecidos são marcados como não verificados |
| Agente | Calculadora real, argumentos inválidos bloqueados, aprovação única, recusa, expiração por contexto, registro alterado e proteção de SHA/diff no GitHub |
| PDF adversarial | Mesmo forçando no teste uma saída de modelo que tenta apagar memória, a operação ficou pendente e nenhum dado foi apagado |
| Provedor remoto | SSE/429/backoff/fluxo parcial e tool calls testados com transporte HTTP controlado; não é evidência de inferência real |
| Embeddings | Dimensão/revisão, persistência e recuperação híbrida testadas com vetores controlados; não é benchmark de qualidade semântica |
| Chromium | Interface de proprietária única, WebGL, memória/reload, Smolin, agenda/aprovação, ferramenta, avaliação, configurações, fallback 2D e navegação móvel passaram |
| Markdown no Chromium | Chat/regeneração com transporte de teste; script não executou e imagens externas não foram carregadas automaticamente |
| Microfone no Chromium | Nenhuma captura antes do clique; tracks iniciadas e encerradas de fato com dispositivo de áudio de teste |
| PWA | Recursos públicos cacheados; nenhuma rota `/api` no cache; fallback offline carregou; sem exceções JavaScript |
| Ruff e diff | Análise passou; sem erros de whitespace |
| Auditorias | npm audit e pip-audit finais: zero vulnerabilidades conhecidas no resultado consultado; python-dotenv foi atualizado para 1.2.2 após um alerta |
| Docker | Build e execução passaram após corrigir propriedade dos arquivos: shell/bootstrap HTTP 200, memória/documentos anônimos HTTP 401 e UID 1000; CA/TLS preservados, sem credenciais/bancos no contexto |

O teste PostgreSQL só roda se `SALY_TEST_DATABASE_URL` for explicitamente fornecida; sem isso, ele é marcado como não executado. Não use DSN de produção. O navegador usa dados/servidor descartáveis, isola chaves reais e usa transporte controlado apenas no check de chat/Markdown. Não existe esse transporte fictício na aplicação de produção.

O build avisa sobre o chunk Three.js acima de 500 kB, separado por carregamento dinâmico. Otimização adicional continua possível. TestClient emite uma depreciação de httpx; os testes efetivamente executam e passam. Auditorias dependem das bases disponíveis e não garantem segurança universal.

## Fora do alcance desta execução

- Não havia `SALY_LLM_API_KEY` utilizável configurada. Documentação Groq retornou 403 pela política de rede. A disponibilidade do identificador/modelo, qualidade em português, resposta gerada real, quotas gratuitas, streaming e cancelamento contra o serviço real não foram certificados.
- Não havia serviço de embeddings/revisão imutável configurado. O código não inventa vetores; a busca textual é o modo disponível imediatamente. pgvector foi real; o encoder dos testes foi controlado.
- Não há projeto Supabase conectado. O esquema/adaptador e a proteção SQL foram verificados em PostgreSQL local, não em uma conta remota. A conexão externa depende de configuração privada, TLS e rede próprios.
- GitHub e Brave foram exercitados por contratos/mocks nos testes de integração da aplicação; nenhuma issue, alteração ou busca real foi enviada por ela. O Git usado para entregar a branch é separado dessas credenciais.
- O áudio de entrada do Chromium é um dispositivo de teste. Voz feminina audível, qualidade de reconhecimento, wake word e comportamento físico do microfone precisam de verificação no navegador/dispositivo da proprietária. SpeechSynthesis não fornece amplitude PCM; animação de saída é aproximada e declarada.
- Não foi instalado um app no dispositivo da proprietária, publicado serviço web, testado um Codespaces remoto dela, executado o novo workflow no GitHub nem validada restauração em tarefa nova da nuvem. Arquivos/blueprint e testes locais não equivalem a essas ações.

## Limitações funcionais

Sem OCR automático, push/cron externo, recorrência, calendário externo, encoder hospedado pelo próprio projeto, OAuth de identidade, fila distribuída, garantia de execução em funções efêmeras, benchmark factual amplo ou proteção universal contra prompt injection. Documentos antigos sem original são preservados como texto legado e não recebem páginas inventadas.

O verificador confirma IDs e resultados operacionais; não garante que todas as afirmações estejam comprovadas pelas fontes. Leitura web exige allowlist e proteção de egress contra redes privadas; a validação de aplicação não substitui a segurança de DNS/proxy da infraestrutura. O banco e backups precisam de proteção em repouso/retention próprios.

## Próxima validação com configuração real

Preencher a chave pelo campo privado do servidor, permitir o domínio do provedor, confirmar `/models`, desbloquear como proprietária e testar uma conversa com streaming/cancelamento e uma ferramenta. Configurar PostgreSQL/Supabase e encoder revisionado, reprocessar um PDF com página conhecida, buscar paráfrases e verificar as referências. Testar backup/restauração em destino separado e áudio real antes de declarar todos os critérios concluídos.

## Rascunho do ambiente

Foram atualizados `install_script`, `start_skill`, variáveis não secretas de modelo/base URL, requisito de `SALY_LLM_API_KEY` e domínios `api.groq.com`/`console.groq.com`, preservando os domínios personalizados anteriores. O rascunho foi salvo; isso não executa scripts, não aplica rede/chaves e não publica a configuração. A proprietária deve revisar e salvar nas configurações e publicar o ambiente quando desejar uma nova versão reutilizável.

## Atualização de conexão do modelo e agente

Foi adicionado `bash scripts/connect-model.sh`: leitura oculta da chave em terminal privado, verificação de `/models`, duas chamadas curtas de streaming, ferramenta real `calculate(2+2)` e confirmação após devolver o resultado ao modelo. A configuração só é gravada após sucesso, por substituição atômica do `.env` com modo 0600. Bindings existentes não são copiados para arquivo. `GROQ_API_KEY` também é reconhecida, exclusivamente para o host Groq. O painel Sistema pode repetir o diagnóstico autenticado, sem transmitir documentos ou memórias.

Nesta rodada: **63 testes Python passaram, 1 teste PostgreSQL foi pulado por falta de DSN descartável nesta execução**, e 6 testes Vitest passaram. O banco real já foi exercitado na rodada v2 acima. Build/Ruff e Chromium passaram. Testes adicionais verificaram o fluxo único modelo → memória/documento → agenda/ferramenta → resposta, privacidade desativada, proteção da chave e falha sem falso sucesso. O transporte do provedor permaneceu controlado nos testes; nenhuma chave real estava presente no ambiente, e `connect-model.sh --check` confirmou a configuração pendente. Isso não comprova inferência real no Codespaces da proprietária.
