# Core Memory e importação

O adaptador de `backend/core/` permanece integrado ao modelo e às ferramentas determinísticas. Fonte original e checksum não foram alterados. O pacote `SALY_Core_v1/` ainda não foi recebido; o prompt mestre foi recebido separadamente e está versionado em `CODEX_INTEGRATION_PROMPT.md`.

## Memórias comuns

Formato aceito:

```json
{"format":"saly-memory-v2","memories":[{"content":"Texto autorizado","category":"informacoes"}]}
```

`format` pode ser omitido para compatibilidade anterior. Exportações da própria SALY são aceitas. Uma prévia mostra quantidade/categorias sem escrever dados. A confirmação importa como não verificado e sem relações externas importadas. Conteúdo textual não é executado. Erros 422 informam caminhos como `memories.0.content`, o tipo esperado e exemplo, sem devolver valores privados da requisição.

## Core administrativo

Em **Configurações → Sistema → Verificação administrativa do Core**, selecione o JSON. A API valida schema/versão e compara o conteúdo canônico com a semente revisada do manifesto. A semente original já ativa é reconhecida; confirmar cria um backup 0600, registra a revisão e verifica a ativação idempotente. Não cria memórias pessoais nem altera pesos.

O backup tem download autenticado. A prévia expira em 15 minutos e só pode ser consumida uma vez. Uma configuração diferente pode ser inspecionada, mas sua migração fica bloqueada até revisão e distribuição do pacote/manifesto no repositório. Essa restrição é deliberada: o upload não permite instalar instruções arbitrárias ou conceder permissões às ferramentas.

Rotas: `/api/memories-import/preview`, `/api/memories-import`, `/api/core/preview`, `/api/core/imports/{id}/confirm` e `/api/core/imports/{id}/backup`. Todas exigem sessão da proprietária. Backup JSON do Core não substitui backup do banco ou de `.env` privado.

## Agente e módulos novos

Consultas tipadas a compras/orçamento, gavetas/links e páginas de livros exigem `privacy.usePersonalTools`, desligado por padrão. A permissão permite uso desses dados no modelo remoto já autorizado; não lê comprovantes, visita URLs, efetua pagamentos ou publica livros. Tutoria por página também pode preparar um trecho no campo de mensagem mediante ação explícita, sem enviá-lo automaticamente. Dados editoriais não concedem privilégios. Revogar permissões de contexto incrementa a época para impedir reaproveitar automaticamente mensagens antigas em futuras inferências; a conversa visível e dados já transmitidos ao provedor não são apagados retroativamente.
