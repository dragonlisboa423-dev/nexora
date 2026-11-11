# Implantação e recuperação

## Opção de desenvolvimento

Codespaces é ambiente temporário, não hospedagem gratuita permanente. Use a branch `feat/saly-smolin`, `bash scripts/install.sh`, configure `.env`, execute `python -m backend.manage owner` na venv e `SALY_SECURE_COOKIE=1 bash scripts/start.sh`. Porta 8000 privada. Não crie worktree: o checkout já é isolado. Mudanças em `.devcontainer` só se aplicam a um Codespaces existente após reconstruir o container.

## Opção PostgreSQL/Supabase

1. Crie ou escolha um projeto dentro de quotas gratuitas que você tenha confirmado. Não ative faturamento automático para executar esta aplicação.
2. Aplique `supabase/migrations/202611110001_global_saly.sql` como administrador. O esquema não tem usuários nem acesso público via PostgREST. Não adicione políticas `anon USING(true)`.
3. Configure `SALY_DATABASE_URL` somente no backend, com DSN de papel servidor e TLS verificado. Não coloque DSN, senha ou service role em variáveis Vite. Revise compatibilidade do pooler e limite de conexões; a aplicação usa SQLAlchemy.
4. Originais e vetores estão no banco, e não num bucket: contabilize BYTEA, JSON/texto e índices na quota. Reduza limites do acervo conforme o plano. Aplique limites da borda/proxy também.
5. Configure o provedor remoto, chave, modelo e, opcionalmente, encoder de 384 dimensões com revisão confirmada. Teste uma conversa e uma recuperação com documentos reais antes de declarar prontidão.
6. Configure acesso por CLI privada ou use `manage hash-owner` para gerar o hash e preenchê-lo em `SALY_OWNER_PASSWORD_HASH` no servidor. Nunca use uma senha de exemplo em produção.
7. Sirva via HTTPS, `SALY_SECURE_COOKIE=1`, um único worker ASGI e sem expor a porta do banco. Use os logs de estado, não credenciais/conteúdo privado em logs.

No ambiente Codex, conexão PostgreSQL pode precisar de regra TCP/encaminhamento específico além da allowlist HTTP. O hostname só pode ser adicionado depois de conhecer o destino real; não se amplia acesso para todos os hosts. Valores de DSN/chaves devem ser fornecidos pelos campos privados do servidor, nunca em chat.

## Container ou blueprint

O Dockerfile usa usuário sem root e imagem com frontend compilado. BuildKit aceita opcionalmente `proxy_ca` para npm e `system_ca` para pip; em um ambiente com proxy TLS mantenha a CA correta, sem `--insecure` ou certificados dentro da imagem final. No ambiente gerenciado os certificados foram montados como secrets de build e a imagem compilou.

Compose contém banco PostgreSQL/pgvector interno, volume persistente e porta da aplicação em loopback. `SALY_POSTGRES_PASSWORD` precisa ser definida pela proprietária. Não há senha fixa de produção no arquivo. Não exponha 5432. Não execute `down -v` sem querer remover dados.

`render.yaml` contém uma configuração web de plano free com variáveis privadas preenchidas fora do Git e PostgreSQL externo. O arquivo não publica nada. Confirme os limites atuais do plano, os termos e o sono por inatividade antes de criar o serviço. O projeto não contrata serviços, não cadastra cartão e não comprova que esse plano continuará gratuito.

Na hospedagem, defina `PORT` (ou SALY_PORT); o launcher respeita a porta informada pelo host. Filas de parsing requerem processo vivo. Funções que terminam logo após a resposta exigem mover os jobs para um worker durável; essa versão não afirma compatibilidade operacional com esse ciclo efêmero.

## Backup

SQLite: `python -m backend.manage backup /destino/privado/backup.sqlite3`, executado com a venv e a mesma configuração da aplicação. Online Backup API conserva transações WAL. Mantenha cópia fora do ciclo de vida do Codespaces/volume temporário. O arquivo inclui a senha derivada e os documentos: trate-o como dado privado.

PostgreSQL: utilize `pg_dump`/backup do serviço, com TLS e autenticação privada. Não passe senhas em comandos publicados ou issue. Documentos estão no banco nesta versão, portanto um dump completo inclui originais, texto e vetores. Teste restauração em projeto separado, incluindo RLS, permissões e configuração. Quotas gratuitas não são garantia de backup.

A exportação JSON autenticada é um complemento lógico, não substitui os binários/vetores de um backup integral.

SQLite recovery: pare a aplicação e use um SALY_DATA_DIR novo com `python -m backend.manage restore <backup> --confirm-stopped`; atualize `.env` antes de subir. A restauração recusa sobrescrever um banco existente e apaga sessões antigas. Guardar backups antigos significa guardar cópias de dados já excluídos; a retenção/descarte precisa ser administrada separadamente.

## Aceitação no seu serviço

Confirme login privado e bloqueio anônimo de memória/documentos; disponibilidade do modelo via `/api/health`; resposta e streaming reais; interrupção; uma ferramenta real; proposta/aprovação de alteração; PDF com página conhecida; original privado; busca híbrida com encoder real; backup/restauração; microfone/voz no dispositivo; PWA sem dados privados no cache. Não considere só a abertura da interface como implantação completa.
