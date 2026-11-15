# Testes da especificação 2026.11.15

## Base e primeira correção

Na base `64812e5`, `bash scripts/test.sh` passou: **97 Python, 1 PostgreSQL pulado por DSN ausente, 6 Vitest e build TypeScript/Vite**. O FFmpeg local informa versão 7.1.5 e licença GPLv2-or-later; isso verifica a ferramenta disponível, não um editor de vídeo implementado.

Após corrigir o importador, os quatro testes selecionados de importação passaram. Cobrem erros por campo sem ecoar conteúdo privado, prévia sem escrita, exportação/importação compatíveis, distinção do Core, confirmação, backup 0600, uso único e bloqueio de política não revisada. Ruff e build passaram. Nenhum teste chamou um modelo remoto ou serviço oneroso.

Comandos executados:

```bash
bash scripts/test.sh
.venv/bin/python -m pytest backend/tests/test_api.py -q -k 'import or core_json'
.venv/bin/ruff check backend
npm --prefix frontend run build
```

Os testes TestClient foram executados fora do sandbox pela limitação já observada de comunicação entre threads. Evidências de fases posteriores serão acrescentadas após execução efetiva; uma interface ou mock não contará como provedor comprovado.
