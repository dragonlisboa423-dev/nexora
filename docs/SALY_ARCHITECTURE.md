# Arquitetura · evolução pela especificação 2026.11.15

A base FastAPI/SQLAlchemy e React/TypeScript/Vite/R3F foi preservada; ver `architecture.md` para decisões anteriores. O prompt íntegro está em `CODEX_INTEGRATION_PROMPT.md`.

Novos módulos: `backend/imports.py` trata formatos/erros; `backend/core/admin.py` revisa o Core distribuído com autenticação, prévia, confirmação e backup; `backend/sync.py` sincroniza revisões. `frontend/src/offline/` implementa um cofre opcional criptografado em IndexedDB e uma interface independente do backend para dados já copiados.

O service worker guarda somente shell/chunks públicos. Na ausência de rede, navega para o shell; `/offline` abre o cofre sem chamar autenticação remota. O desbloqueio usa uma senha local e não equivale a obter sessão no servidor. Sincronização continua exigindo a sessão HttpOnly da proprietária e validação de origem no backend. Nenhum segredo de provedor é copiado para o browser.

Políticas, memórias, documentos, filas e logs continuam separados. `storage.transaction()` reaproveita uma conexão para alteração de domínio, derivados, changelog e recibo de sincronização. O escopo inicial de escrita offline é memória e lembrete; documentos são copiados seletivamente para leitura. Configurações ficam disponíveis como snapshot de consulta. Não há inferência offline.

Fases posteriores devem reaproveitar contratos/entidades existentes, manter migrações aditivas e registrar capacidades comprovadas. O cofre não tornou automaticamente todas as futuras abas sincronizáveis.
