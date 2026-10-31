# Validação e limites — 31/10/2026

O código foi implementado e testado na branch `feat/saly-intelligence`. A solicitação integral ainda **não está concluída**: inferência real e validação física de áudio são pendências obrigatórias antes de afirmar que a assistente completa está operacional.

## Evidências executadas

| Verificação | Resultado |
|---|---|
| `bash scripts/install.sh` | Passou, inclusive repetição com dependências já presentes, `npm ci`, build e migração idempotente |
| `bash scripts/test.sh` | Build TypeScript/Vite passou; 26 testes pytest passaram |
| SQLite FTS5, memória, edição/exclusão, versões e restauração | Passaram em integração |
| Consolidação aprovada, arquivo e preservação dos originais | Passou em integração |
| Banco após novo processo | Persistência comprovada |
| Backup SQLite e recuperação em diretório novo | Passaram; sessões invalidadas e sobrescrita recusada |
| Autenticação, logout, limitação de tentativas, CSRF, isolamento entre dois usuários | Passaram |
| Extração de PDF com texto, importação Markdown e pesquisa com fontes | Passaram |
| Parâmetros vocais e perfis persistentes com validação | Passaram pela API |
| Streaming de tokens, contexto filtrado e salvamento ao concluir | Passou com transporte de modelo controlado no teste, não com pesos reais |
| Modelo offline | HTTP 503, sem resposta fictícia ou criação de conversa |
| Calculadora AST, limites, lista interna e painel de avaliação | Passaram; avaliação operacional gera 8 resultados reais |
| Chromium desktop 1440 px e celular 390 px | Cadastro, núcleo WebGL, memória, reload, documento, FTS, avaliação, configurações e menu móvel passaram; sem exceções JavaScript ou overflow horizontal |
| Microfone no Chromium | Nenhuma captura antes do clique; ativação e encerramento das tracks comprovados com dispositivo de áudio de teste do Chromium |
| Ruff | Passou |
| `npm audit` | Zero vulnerabilidades conhecidas no resultado consultado após atualização |
| `pip-audit -r backend/requirements.txt --vulnerability-service pypi` | Zero vulnerabilidades conhecidas no resultado consultado após atualização |

A auditoria depende da base disponível no momento e não constitui certificação de segurança. As versões resolvidas foram fixadas nos manifests/lockfile; repita auditorias antes de implantar.

O build informa que o chunk Three.js é maior que 500 kB. O núcleo usa importação dinâmica e fica separado do bundle principal; redução adicional é melhoria de desempenho. A suíte emite um aviso de depreciação de TestClient/httpx; os testes executam e passam, sem silenciar o aviso.

## Bloqueio de inferência

Não há Ollama ou pesos do modelo instalados nesta máquina. As consultas HTTPS aos destinos oficiais `huggingface.co` e `registry.ollama.ai` foram negadas com HTTP 403 pela política de rede. Não houve bypass ou download de pesos por terceiros.

Foram salvos no rascunho do ambiente: `install_script`, `start_skill` e adições desses dois domínios à lista personalizada, preservando o preset de gerenciadores de pacotes. Salvar o rascunho não aplica a rede nem publica um snapshot. Revise e salve nas configurações do ambiente e depois publique quando apropriado. Os domínios de redirecionamento de blobs podem exigir investigação adicional. A implantação em uma tarefa nova não foi validada.

Após disponibilizar runtime/pesos: execute `ollama show smollm3:3b`, confirme o indicador do modelo, envie uma mensagem, verifique tokens em streaming, interrupção, histórico e recuperação de uma memória autorizada/documento. Observe RAM/latência reais e compare a identidade dos pesos com o modelo solicitado. Nenhum benchmark de geração foi executado aqui.

## Validação manual ainda necessária

- Microfone físico, permissão negada e suporte de transcrição em cada navegador alvo. O teste com áudio sintético não comprova qualidade do reconhecimento ou comportamento do dispositivo real.
- Voz feminina pt-BR disponível no dispositivo, seleção/amostra, início real, pausa/retomada, fim e interrupção. Headless não comprova reprodução audível. A aplicação trata esses eventos; precisa ser validada com voz instalada.
- Em SpeechSynthesis, as ondas são aproximações ligadas aos eventos; análise acústica exata da saída não está implementada.
- SmolLM3 real em CPU, acurácia linguística, alinhamento entre citações e afirmações, latência de cancelamento e consumo de recursos.
- Inicialização real do devcontainer, Docker Compose e execução do workflow no GitHub. Arquivos fornecidos, mas não executados neste ambiente.
- Restauração de snapshot da nuvem em tarefa nova, persistência do volume e HTTPS/encaminhamento privado no Codespaces.

## Funcionalidades pendentes

TTS local e pacotes licenciados; interface de adaptador PCM; ativação por nome mediante consentimento; treinamento LoRA/QLoRA; resumo automático de históricos; consolidação semântica assistida pelo modelo; detecção geral de contradições e avaliação factual de respostas; referências por página de PDF (atualmente por trecho); relatórios narrativos e organização avançada de arquivos; recuperação de senha/gestão de contas; migração de bancos legados (não fornecidos em formato acessível). A consolidação manual aprovada e exportação de relatório de atividades JSON já estão disponíveis.

Nenhuma função pendente é apresentada como ferramenta executável na interface. “Memória progressiva” significa armazenamento/recuperação autorizados; não treinamento dos pesos.

## Correção do instalador para Codespaces existentes

O instalador original seguia `python3` sem validar a versão. Após um relato de falha compilando `pydantic-core` (sem log suficiente para confirmar a causa exata), o instalador passou a selecionar Python 3.12, atualizar pip e exigir wheel para essa extensão. Ambientes virtuais incompatíveis são preservados, não excluídos.

Regressões verificadas: rejeição de interpretador explicitamente incompatível; preservação de `.venv` quebrada; criação de Python 3.12; repetição sem novo backup; preservação de `.env` e dados. A rota sem Python 3.12 no PATH foi exercitada em diretório descartável: uv baixou CPython 3.12.15 e criou o ambiente com verificações de integridade/TLS habilitadas. O script completo de instalação/build também passou novamente. Isso não equivale a observar a execução no Codespaces do usuário.
