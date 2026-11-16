# Segurança e limites comprovados

Mantidos: sessão única, cookie HttpOnly/SameSite, Secure em HTTPS, validação de origem, limites de corpo/frequência, autenticação de documentos e argumentos tipados no executor. O agente não recebe ferramenta de shell nem pode chamar as rotas administrativas/sync por concessão própria. Não há contratação de serviço ou ampliação automática de despesas.

O importador mostra erros sem ecoar dados inválidos; Core não entra como memória comum e uma política não revisada não é instalada. Textos de documentos/links continuam dados não confiáveis. Uma identificação no schema ou uma resposta convincente do modelo não comprova execução.

Dados offline são opt-in e criptografados em IndexedDB. Senha do cofre é independente da senha de login; não é enviada ao servidor. Bloquear/recarregar retira a chave da interface. Isso não garante limpeza forense da RAM, proteção contra extensões maliciosas, sistema operacional comprometido ou XSS no mesmo contexto desbloqueado. Backup e senha devem ser guardados separadamente. Não armazenar tokens/senhas como conteúdo de memórias; a aplicação não é um gerenciador de senhas.

Sync só aceita entidades/campos conhecidos, revisão base e confirmação para exclusões/lembretes. Operação e recibo são atômicos. Conflitos não sobrescrevem silenciosamente dados, e a restauração de um cofre pausa envios. Tombstones propagam exclusões; rascunhos concorrentes ficam explícitos para decisão. API/arquivos privados nunca entram no Cache Storage público.

Testes cobrem acesso anônimo, formato, hostilidade de PDF contra o limite de aprovação, transações, idempotência e conflitos. Eles não provam invulnerabilidade universal. Retenção/segredos em conteúdo pessoal, expiração de sessões, criptografia da infraestrutura e descarte de backups exigem políticas e revisões contínuas. A base existente mantém seu histórico de conversas; não se passou a alegar retenção mínima automática apenas por integrar o Core.

## Recursos novos

Consultas pessoais do agente têm opt-in específico, desligado por padrão; não há ferramenta de pagamento, publicação editorial ou shell. Revogar permissões de contexto invalida a época para inferências futuras, preservando o histórico visível. Não se promete retirar dados já enviados a terceiros. Texto de livro continua dado não confiável para comandos.

Comprovantes e mídias são BLOBs autenticados, normalizados/validados e fora do cache público. Quota privada padrão de 200 MiB (`SALY_MAX_PRIVATE_MEDIA_MB`) é verificada dentro da transação, separada da quota de documentos. Imagens têm proteção de dimensões e remoção de metadados. AV usa caminhos gerados pelo servidor, formatos permitidos e protocolos file/pipe; não aceita URLs/playlists ou nomes de arquivo como comandos. Legendas entram por arquivo de texto com expansão desativada. Subprocessos recebem ambiente mínimo sem chaves, tempo/recursos e limites de saída.

Mídia referenciada por versão editorial é preservada até exclusão do livro. Excluir um registro não apaga backups exportados, arquivos baixados ou conversas que receberam trechos por ação explícita. O cofre exige consentimento separado para novas categorias; livros/mídias guardados são dados privados, e exportar cópia JSON local fora do cofre produz arquivo que deve ser guardado privadamente. Nada disso comprova invulnerabilidade universal ou limpeza forense.

A revisão de um backup restaurado inclui operações de livros (progresso e novas notas), além da fila geral. Contadores incluem essas alterações/conflitos. A interface preserva o texto do rascunho quando a gravação criptografada falha; não o apresenta como salvo. O teste usa aborto controlado do IndexedDB, com resultado documentado no relatório.
