# Segurança e limites comprovados

Mantidos: sessão única, cookie HttpOnly/SameSite, Secure em HTTPS, validação de origem, limites de corpo/frequência, autenticação de documentos e argumentos tipados no executor. O agente não recebe ferramenta de shell nem pode chamar as rotas administrativas/sync por concessão própria. Não há contratação de serviço ou ampliação automática de despesas.

O importador mostra erros sem ecoar dados inválidos; Core não entra como memória comum e uma política não revisada não é instalada. Textos de documentos/links continuam dados não confiáveis. Uma identificação no schema ou uma resposta convincente do modelo não comprova execução.

Dados offline são opt-in e criptografados em IndexedDB. Senha do cofre é independente da senha de login; não é enviada ao servidor. Bloquear/recarregar retira a chave da interface. Isso não garante limpeza forense da RAM, proteção contra extensões maliciosas, sistema operacional comprometido ou XSS no mesmo contexto desbloqueado. Backup e senha devem ser guardados separadamente. Não armazenar tokens/senhas como conteúdo de memórias; a aplicação não é um gerenciador de senhas.

Sync só aceita entidades/campos conhecidos, revisão base e confirmação para exclusões/lembretes. Operação e recibo são atômicos. Conflitos não sobrescrevem silenciosamente dados, e a restauração de um cofre pausa envios. Tombstones propagam exclusões; rascunhos concorrentes ficam explícitos para decisão. API/arquivos privados nunca entram no Cache Storage público.

Testes cobrem acesso anônimo, formato, hostilidade de PDF contra o limite de aprovação, transações, idempotência e conflitos. Eles não provam invulnerabilidade universal. Retenção/segredos em conteúdo pessoal, expiração de sessões, criptografia da infraestrutura e descarte de backups exigem políticas e revisões contínuas. A base existente mantém seu histórico de conversas; não se passou a alegar retenção mínima automática apenas por integrar o Core.
