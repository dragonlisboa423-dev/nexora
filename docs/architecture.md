# Arquitetura v2

## Decisões

Foi reaproveitada a base React/TypeScript/R3F, FastAPI, calculadora, controles de voz e gerenciamento de memórias. O backend foi separado em armazenamento, segurança, serviços de memória, adaptador LLM, registro do agente, integrações e Centro Smolin. O único modelo de linguagem fica remoto. A implantação preferida usa PostgreSQL/pgvector; SQLite mantém desenvolvimento funcional sem contratar serviços.

Uma proprietária é uma política de acesso, não uma linha de tabela `users`. `owner_access` tem apenas a chave singleton 1 e o hash de senha. `owner_sessions` armazena hashes de tokens aleatórios com prazo de 24 horas. Todas as tabelas de domínio são globais, sem `user_id`. Não há rota de registro ou troca de perfil.

SQLAlchemy mantém um esquema portátil. Entidades pequenas usam payload JSON validado por Pydantic nos limites da API/registro de ferramentas, mais IDs e datas tipados. Originais e fragmentos usam colunas próprias com FKs/cascatas; vetores têm dimensão fixa. Essa escolha preserva os painéis existentes e reduz migração duplicada entre SQLite/PostgreSQL. Evoluções de campos de domínio podem promover propriedades JSON para colunas/índices conforme volume real.

## Persistência

`app_config`, `owner_access`, `owner_sessions`, `conversations`, `messages`, `memories`, `versions`, `memory_vectors`, `documents`, `document_originals`, `document_chunks`, `document_jobs`, `tool_executions`, `agent_approvals`, `reminders`, `activities`, `evaluations` e `lists`.

FTS5/trigger no SQLite; full-text em português, pgvector e HNSW no PostgreSQL. Revisão do encoder é salva em cada vetor, com contrato de 384 dimensões e confirmação da revisão pelo servidor. A busca nunca substitui embeddings ausentes por números gerados artificialmente. Sem encoder, a recuperação é lexical; status indica indisponibilidade. O fingerprint precisa continuar identificando o mesmo encoder/normalização na reindexação.

Originais estão em BLOB/BYTEA privado no banco, não em Storage separado. O RLS é habilitado no PostgreSQL; não há políticas de leitura pública, e a migração revoga privilégios de anon/authenticated. Conexão do backend usa papel servidor confiável. O browser não conecta diretamente ao banco e nunca recebe DSN ou credenciais administrativas.

## Modelo, agente e memória

`backend/llm/provider.py` transmite SSE OpenAI-compatible de um único modelo, validando disponibilidade via `/models`. Retry é limitado a respostas recusadas antes de transmitir geração. Depois do primeiro token não há replay silencioso. Nenhuma ferramenta é executada por texto livre: só chamadas estruturadas em registro tipado, com limite de argumentos, etapas e duração.

O contexto combina memórias utilizáveis, documentos recuperados e histórico limitado em caracteres. Memória e conhecimento são responsabilidades separadas; PDFs não são copiados para preferências. Exclusões removem índices/representações derivadas identificadas, expiram aprovações e incrementam `context_epoch`. Prompts não usam mensagens de epochs anteriores; uma geração interrompida por mudança de contexto não é salva como concluída. Históricos independentes e backups antigos não são apagados indiscriminadamente.

Operações sensíveis são propostas em `agent_approvals`. A decisão usa update condicional `status=pending`, expira em 15 minutos e só pode ser consumida uma vez. Alterações GitHub guardam SHA/diff antes da aprovação e recusam um arquivo que mudou desde a revisão. Erros de resultado externo incerto são marcados como falha, sem repetição automática. O agente nunca recebe shell, SQL arbitrário ou chaves.

Ferramentas de leitura retornam dados não confiáveis, não novas instruções. O teste adversarial comprova especificamente que uma saída maliciosa solicitando exclusão não a executa sem aprovação. Ele não comprova que toda frase do modelo resiste a influência de documentos; revisão humana e limites de autonomia continuam necessários.

## Centro Smolin

Recepção autenticada e limitada → validação de bytes → hash/duplicatas → original privado → job persistente → parser PDF em subprocesso com limites Linux → páginas/texto/metadados → fragmentos sobrepostos → embeddings opcionais → persistência/indexação → recuperação com IDs/páginas.

Transferência tem progresso de bytes por XHR; processamento tem páginas concluídas e estado real de job. Arquivos sem texto permanecem em `ocr_required`; extração incompleta é `partial`. Cancelamento interrompe o task/parser e preserva o original; uma extração em andamento não deve recriar documento excluído. Jobs pendentes são retomados na inicialização do processo ASGI. Não é uma fila distribuída: execute um único worker de aplicação enquanto não houver coordenação distribuída.

O parser não interpreta JavaScript, macros, anexos executáveis ou instruções do documento. O original preservado pode conter conteúdo ativo: o backend nunca o executa; a abertura é uma ação da proprietária no visualizador do navegador, com sandbox e nosniff. PDFs corrompidos, protegidos ou além dos limites geram falha controlada. OCR e reconstrução precisa de tabelas não estão implementados.

## Eventos e interface

`operations.ts` centraliza operações identificadas, prioridades e eventos. Microfone, transcrição, requisição, tokens, consulta, documentos, ferramentas, voz e rede provocam transições reais. O temporizador de 650 ms só desvanece um sucesso já confirmado, com versão que evita apagar uma operação posterior. Testes cobrem concorrência/cancelamento e não inferem conclusão por tempo decorrido.

O núcleo tem deformação procedural e iluminação GLSL; não é GIF ou esfera rígida. Movimento reduzido desativa animações contínuas. Fallback 2D, baixa qualidade e DPR limitado mantêm acesso. Amplitude do microfone usa RMS de AnalyserNode. SpeechSynthesis não entrega PCM; sinais de saída usam eventos de início/palavra/pausa/fim e animação aproximada, declarada na interface.

Markdown usa react-markdown/remark-gfm sem HTML bruto. Imagens externas viram links e não são carregadas automaticamente. Recursos de código são escapados. A PWA cacheia somente shell e arquivos públicos de build; nunca APIs, documentos, banco ou chaves. Sem conexão, mostra uma página pública de indisponibilidade, sem prometer inferência offline.

## Segurança e limites

scrypt com salt, cookie HttpOnly/SameSite Strict, Secure em HTTPS, limitação de tentativas/requisições, validação de origem e tipo de requisição, limites antes de parsing, dados privados fora do Git e integrações com destinos fixos/autorizados. Leituras web exigem HTTPS, resoluções públicas, sem redirects, tamanho/timeout limitados e allowlist explícita. O deployment deve manter egress que bloqueie redes privadas: DNS rebinding e ataques de infraestrutura exigem proteção da hospedagem além da validação de aplicação.

Sem chaves, o provedor e integrações ficam indisponíveis. Não se cria senha real para a proprietária durante testes. `.env` é carregado sem sobrescrever bindings injetados. Arquivos de backup têm modo 0600; sessões são invalidadas após recuperação. Banco e backup não são criptografados pela aplicação: use armazenamento privado/cifrado da infraestrutura.

Ainda faltam operação de múltiplos workers, workers duráveis em funções efêmeras, autenticação externa de identidade, push fora do app, OCR, avaliação factual ampla, encoder/modelo reais com suas quotas e validação física de áudio. Essas limitações não são mascaradas por indicadores fictícios.
