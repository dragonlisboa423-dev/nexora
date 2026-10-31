# Arquitetura e operação

## Componentes

Frontend React/TypeScript/Vite. `Core.tsx`: visualização R3F, shader e fallback 2D. `audio.ts`: fronteira da Web Audio/SpeechSynthesis/SpeechRecognition. `Panels.tsx`: gerenciamento persistente. `main.tsx`: sessão, navegação, chat streaming e transições operacionais. Síntese local futura deve implementar a mesma interface de iniciar/interromper/pausar e fornecer áudio via HTMLMediaElement/AudioBuffer ao AnalyserNode, sem substituir o modelo principal.

Backend FastAPI. `storage.py`: esquema v1, FTS5 e transações. `main.py`: autenticação, permissões por proprietário, API, montagem do contexto e cliente HTTP de inferência. `tools.py`: calculadora por AST. `manage.py`: integridade, inicialização idempotente e backups consistentes.

Ollama fica separado; apenas a URL administrada em ambiente é utilizada. O backend ignora proxies do processo somente para esse serviço local/configurado; isso não é uma rota de download de Internet. O frontend nunca recebe credenciais de modelo. A inferência principal é SmolLM3-3B. Recuperação lexical FTS5 não introduz outro modelo generativo ou de embeddings.

## Fluxo de chat

Autenticar → verificar tag do modelo → recuperar contexto permitido → persistir mensagem do usuário → montar histórico limitado → iniciar NDJSON → informar fontes/IDs → transmitir tokens → salvar resposta somente após `done`. Sem modelo, HTTP 503 antes de criar conversa. Falhas durante o fluxo geram evento `error`; não são mascaradas por texto pré-fabricado. `think:false` solicita resposta sem canal de raciocínio. Texto de documentos e memórias é delimitado como dados não confiáveis, sem execução de instruções.

O contexto é limitado por caracteres para evitar crescimento ilimitado. Não há resumo automático de históricos; apenas as últimas mensagens que cabem no orçamento são reenviadas. O Ollama aplica seu limite de tokens. Conteúdo externo malicioso ainda pode influenciar texto produzido; por isso o modelo não tem acesso automático a shell, sistema de arquivos ou ferramentas destrutivas.

## Persistência

SQLite em WAL, foreign keys e FTS5 com triggers sincronizadas. Versões preservam o estado anterior de uma memória em cada edição. Exclusão permanente remove versões desse registro. Relações são referências por ID; exclusão do alvo pode deixar uma referência histórica sem alvo. Imports removem relações de outra instalação e marcas de verificação. Memórias contestadas/arquivadas/desautorizadas não são recuperadas. Conversas e trechos já produzidos não são reescritos retroativamente.

Tabela `schema_version` marca v1; `init` é idempotente. Futuras mudanças exigem migrações transacionais, backup prévio e testes de reversão. Não há downgrade automático nesta versão.

Backup administrativo usa SQLite Online Backup API, não cópia de arquivo em WAL ativo. Saída é criada com modo 0600, não sobrescreve arquivos e passa por integrity_check. Restauração exige confirmação de serviços parados e diretório vazio; sessões são invalidadas. Nunca acrescente backups/bancos privados ao Git. Exportação JSON da conta não inclui hashes de senha ou sessões.

## Limites de segurança

Cadastro web inicial exclusivo. Isolamento por user_id nos dados e verificações de propriedade em alterações. Multiusuário é suportado no esquema/testes, mas o gerenciamento de contas adicionais e redefinição de senha são pendências. Sessões expiram em sete dias; logout invalida token no servidor. scrypt com salt aleatório; tentativas de login limitadas por usuário em memória no processo. Use um worker enquanto esse limitador não for compartilhado.

SameSite=strict, cookies HttpOnly, Secure configurável, comparação Origin/Host e content-type/header de escritas. Sem CORS permissivo. Domínio/terminação TLS e limites de corpo devem ser configurados no proxy de uma implantação exposta. O backend e os scripts vinculam loopback por padrão. Documentação API não expõe conteúdo privado sem autenticação.

Uploads são extraídos em memória, com limites de tamanho/texto/páginas, sem manter o binário. PDFs hostis ainda podem demandar recursos: isolamento do parser em worker com timeout/cota é melhoria necessária antes de aceitar uploads públicos. IDs e tipos de atividade são registrados; senhas e tokens não são escritos no log de aplicação. O banco é privado, mas não cifrado em repouso.

## Eventos audiovisuais

`listening`: somente após getUserMedia resolver; AnalyserNode calcula RMS real. `thinking`: requisição iniciada após verificação disponível no frontend; o backend ainda pode recusar. `responding`: primeiro token recebido com pulso. `speaking`: callback onstart do sintetizador; pausa/retomada/término/erro obedecem eventos e tokens de geração para ignorar callbacks antigos. Interrupção cancela requisição, captura e síntese. Nenhuma ativação passiva por nome.

No SpeechSynthesis, ondas são aproximações visuais, sem acesso a amplitude PCM. Em movimento reduzido, o estado textual permanece disponível e animações são desativadas. WebGL ausente/erro ou qualidade 2D usa fallback. Qualidade baixa reduz subdivisões, partículas e densidade de pixels.
