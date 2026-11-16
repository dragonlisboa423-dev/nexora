# Persistência e migrações aditivas

O esquema principal continua sendo SQLAlchemy, com SQLite ou PostgreSQL/pgvector. `storage.initialize()` cria apenas tabelas/índices ausentes; não descarta o banco. PostgreSQL recebe RLS e revogação de acesso público para todas as tabelas criadas pelo backend, conforme a política anterior. O processo precisa do papel servidor apropriado.

Novas estruturas desta fase:

| Estrutura | Conteúdo |
|---|---|
| `core_imports` | Prévia, hash, compatibilidade, estado e resultado da revisão do Core; não instala políticas arbitrárias. |
| `sync_changes` | Cursor monotônico, tipo, ID, revisão, exclusão e timestamp. Não guarda cópia do conteúdo pessoal. |
| `sync_receipts` | ID único de operação, hash da requisição e metadados mínimos do resultado, sem o texto da memória. |
| `revision` no payload JSON | Revisão gerenciada pelo servidor para memórias, lembretes e documentos; registros legados são lidos como revisão 1 e materializados na próxima escrita. |

Uma exclusão gera tombstone no changelog. A cópia local é removida no próximo pull; um rascunho offline concorrente vira conflito explícito, não recriação automática. Se a proprietária decidir preservar o rascunho após uma exclusão, é criado outro ID. O rascunho conflitante permanece criptografado até a decisão ou remoção do cofre; essa é a política de retenção local desta fase.

O bootstrap captura o cursor antes de ler as entidades. Atualizações concorrentes reaparecem no próximo pull, evitando lacunas. Cada push usa transação para mutação, limpeza de derivados, changelog e recibo. SQLite serializa a transação de escrita; PostgreSQL usa lock transacional para o fluxo e lock da linha ao verificar a revisão. Operações repetidas com mesmo ID/conteúdo não são aplicadas duas vezes. Reutilizar o ID com outro conteúdo é rejeitado.

`IndexedDB saly-private-vault`, versão 1, contém um envelope AES-GCM. A chave é derivada por PBKDF2-SHA256 com 210.000 iterações e salt aleatório de 16 bytes. Cada escrita usa nonce aleatório de 12 bytes e autentica cabeçalho/revisão. A chave não é extraível nem persistida. Há comparação de revisão/salt para impedir sobrescrita silenciosa por outra aba. Backups são envelopes criptografados, validados antes de substituir o cofre; restauração recriptografa e pausa sincronização até revisão.

O cofre limita o JSON a 30 MB e cada original escolhido a 10 MB, verificando SHA-256 contra o metadado do servidor. Limites de espaço do browser continuam aplicáveis. `navigator.storage.persist()` é solicitado, mas pode ser recusado. Backups SQLite administrativos continuam necessários; documentos e backup de Core em arquivos precisam ser considerados na política de recuperação da hospedagem. Não execute `DROP`, reset ou exclusão de volume para atualizar.

## Agenda e alarmes

Tabelas JSON aditivas `calendar_events`, `alarms`, `alarm_occurrences`; as duas primeiras têm revisão gerenciada pelo servidor. Elas não são acrescentadas silenciosamente ao protocolo offline existente, restrito a memórias/lembretes/documentos. Ocorrências usam IDs determinísticos e estado persistente, com lease/claim, apresentação relatada, adiamento e conclusão. Contêm metadados privados; exigem a mesma sessão de proprietária.
