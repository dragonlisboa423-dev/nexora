# SALY Intelligence

Assistente pessoal com React/TypeScript, núcleo 3D, FastAPI, SQLite FTS5 e integração local com **um único modelo generativo: SmolLM3-3B**, via Ollama. Sem chaves obrigatórias de serviços comerciais de IA.

Esta é uma fundação funcional em desenvolvimento. Memórias, documentos, autenticação, ferramentas e configurações funcionam independentemente do modelo. **O chat exige Ollama e pesos instalados; não produz respostas simuladas quando offline.** O download do modelo foi bloqueado pela rede do ambiente de implementação; inferência real ainda precisa ser validada. Consulte [validação e limitações](docs/validation.md).

## Iniciar em Linux

Requisitos: Python 3.12+, Node.js 24, npm e SQLite com FTS5 (incluído normalmente no Python). Para inferência em CPU, reserve inicialmente pelo menos 8 GB de RAM e espaço para os pesos; latência e consumo devem ser medidos no seu hardware. GPU não é obrigatória.

Na raiz do checkout:

```bash
bash scripts/install.sh
cp .env.example .env
bash scripts/start.sh
```

O servidor atende na porta **8000**, em loopback por padrão, servindo frontend e API na mesma origem. Abra essa porta no seu navegador local, ou use o encaminhamento **privado** do Codespaces. Crie a conta proprietária no primeiro acesso, com senha de pelo menos 12 caracteres. Cadastros adicionais pela web ficam desabilitados após a primeira conta.

Mantenha a porta privada durante o cadastro inicial. Para HTTPS configure `SALY_SECURE_COOKIE=1` em `.env`; para HTTP local mantenha `0`. Antes de disponibilizar fora da máquina, use HTTPS, proxy reverso, limites de corpo/timeout, armazenamento persistente e revisão de segurança da implantação. O serviço não oferece recuperação de senha nem provisionamento multiusuário pela interface nesta versão.

## Conectar o modelo

Instale Ollama a partir de sua distribuição oficial, mantendo verificações de integridade e TLS. Em terminais separados:

```bash
ollama serve
ollama pull smollm3:3b
bash scripts/start.sh
```

`ollama serve` só é necessário se o serviço ainda não estiver ativo. O download é explícito e pode consumir vários GB. Verifique o modelo e a licença nos metadados do registro; não instale outro modelo generativo automaticamente.

```bash
ollama show smollm3:3b
ollama list
```

A configuração padrão é `SALY_MODEL_URL=http://127.0.0.1:11434` e `SALY_MODEL=smollm3:3b`. A API verifica a presença da tag antes do chat. Alterações de modelo são feitas pelo administrador em `.env`, nunca por instruções de documentos. Não exponha a porta do Ollama publicamente: ele não fornece a autenticação da SALY.

A rede atual bloqueou `huggingface.co` e `registry.ollama.ai` com HTTP 403. É preciso permitir os destinos oficiais necessários nas configurações do ambiente antes de baixar os pesos. Redirecionamentos de blobs podem exigir domínios adicionais; diagnostique a resposta em vez de desabilitar TLS ou contornar a política. Ter o código do conector não comprova inferência real.

## Desenvolvimento

Backend com recarga, na raiz:

```bash
.venv/bin/uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend em outro terminal:

```bash
cd frontend
npm run dev
```

O Vite encaminha `/api` para o backend. Configure um encaminhamento privado também para a porta do Vite quando necessário. A documentação OpenAPI está em `/docs` no servidor backend; dados privados exigem sessão autenticada.

## Funcionalidades

- Núcleo Three.js/R3F com camadas translúcidas, shader, estrutura interna, partículas, anéis, pulso no primeiro token e no início real da fala. Carregamento do núcleo separado do restante da aplicação.
- Máquina de estados `idle`, `listening`, `thinking`, `responding`, `speaking`, `paused`, `executing`, `error`. `executing` fica reservado a futuras tarefas com visualização no núcleo; as ferramentas atuais exibem seus resultados nos painéis.
- Chat NDJSON via Ollama, contexto autorizado, histórico persistente, erros explícitos e cancelamento do pedido. Respostas parciais interrompidas não são registradas como concluídas. O encerramento da conexão solicita interrupção no servidor do modelo, mas a liberação de recursos depende do Ollama.
- Memórias em cinco categorias, edição, tags, origem, datas, verificação, contestação, arquivo, autorização de uso, relações por ID, histórico, restauração de versões, importação/exportação e exclusão múltipla confirmada. Duplicatas exatas podem ser localizadas. A consolidação exige conteúdo revisado e confirmação; cria uma memória não verificada e arquiva os originais com versões preservadas.
- Conhecimentos: extração PDF textual/TXT/Markdown, trechos FTS5 e referências com documento/posição. Até 10 MB, 500 páginas e 2 milhões de caracteres. PDFs digitalizados requerem OCR externo. Não lê arquivos arbitrários do computador: somente uploads autorizados.
- Microfone solicitado por ação explícita, amplitude de entrada por AnalyserNode, pressionar para falar, transcrição quando suportada e alternativa por texto. O reconhecimento do navegador pode usar serviços externos.
- `/voices`: vozes realmente disponíveis no sistema/navegador, amostras, velocidade, tonalidade, volume e perfis persistidos no backend. A API não fornece gênero padronizado; escolha uma voz feminina ouvindo as amostras. Não há voz clonada ou pacote fictício.
- SpeechSynthesis usa eventos de reprodução para sincronizar o núcleo. **A amplitude da fala sintetizada é aproximada; esta API não disponibiliza PCM.** A amplitude do microfone é analisada de verdade. TTS local, importação de pacotes, voz com PCM e detecção contínua de “Saly” ainda não estão implementados.
- Ferramentas explícitas: calculadora por AST com limites (sem `eval`, shell ou execução de documentos), lista persistente e registros de atividade. Documentos e memórias são dados no contexto; resistência absoluta a prompt injection não é garantida. O modelo não recebe ferramenta de execução arbitrária.
- Avaliação determinística com métricas reais de aritmética, limites e integridade SQLite. **Não representa precisão factual universal nem benchmark de linguagem.** Fontes recuperadas não certificam que todas as afirmações da resposta estejam fundamentadas.
- Configurações de personalidade, privacidade e qualidade gráfica, movimento reduzido e alternativa 2D. Controles de privacidade não apagam automaticamente dados históricos.

## Rotas

`/`, `/memory`, `/knowledge`, `/voices`, `/activity`, `/evaluation`, `/settings`, `/settings/personality`, `/settings/privacy`, `/settings/system`.

## Dados e recuperação

`SALY_DATA_DIR` deve apontar para um volume persistente privado. O padrão é `data/`, ignorado pelo Git; o SQLite não é criptografado em repouso. Proteja a máquina, o volume e os backups. A aplicação usa senhas com scrypt, tokens de sessão aleatórios com hash no banco, cookies HttpOnly/SameSite e validação de origem em escritas. Não usa localStorage para memórias ou autenticação.

```bash
.venv/bin/python -m backend.manage check
.venv/bin/python -m backend.manage backup /caminho/privado/saly-backup.sqlite3
```

Para recuperar, **pare a aplicação**, preserve o banco anterior e restaure em um diretório novo:

```bash
SALY_DATA_DIR=/caminho/novo .venv/bin/python -m backend.manage restore /caminho/privado/saly-backup.sqlite3 --confirm-stopped
```

Atualize `SALY_DATA_DIR` em `.env` antes de reiniciar. Restauração não sobrescreve bancos existentes e invalida sessões antigas. A exportação JSON na página de privacidade é específica da conta; a recuperação completa utiliza o backup SQLite administrativo. Memórias JSON podem ser importadas pela página de memórias, sempre como não verificadas. Backups antigos continuam contendo dados excluídos e precisam ser descartados separadamente conforme sua política de retenção. Detalhes em [arquitetura](docs/architecture.md).

## Testes

```bash
bash scripts/test.sh
```

A suíte testa rotas, autenticação, isolamento, CSRF, memória, versionamento, busca, documentos, persistência entre processos, streaming com transporte controlado, falha offline, ferramentas e avaliação. Não substitui a validação com o modelo real.

Teste de navegador opcional (Chromium instalado):

```bash
.venv/bin/pip install -r backend/requirements-browser.txt
.venv/bin/python scripts/browser_smoke.py
```

O script usa banco temporário e servidor próprio, sem seus dados. Evidências, cenários manuais e pendências estão em [docs/validation.md](docs/validation.md).

## Codespaces e Docker

`.devcontainer/devcontainer.json` prepara Python/Node e instalação. Execute `bash scripts/start.sh`; a porta 8000 deve continuar privada. O Codespaces é um ambiente de desenvolvimento temporário: faça backups antes de removê-lo. GitHub Actions executa testes; não hospeda um servidor de IA. GitHub Pages não executa o backend.

Docker Compose opcional, ainda não validado neste ambiente:

```bash
docker compose up --build -d
docker compose exec ollama ollama pull smollm3:3b
```

Volumes `saly-data` e `ollama-models` preservam os dados entre reinícios; `docker compose down -v` os destrói. A porta publicada fica em loopback. A configuração Docker não deve ser tomada como implantação pronta para Internet.

## Migração e próximos passos

O checkout original continha apenas README; não havia código ou banco antigo a migrar. Os ZIPs anteriores excediam o limite de transferência e **não foram importados**. Caso existam dados da assistente anterior, preserve uma cópia antes de converter para o formato de importação. Não há conversor de banco antigo sem conhecer seu esquema.

Pendências: inferência real e benchmark em CPU, validação física de voz/microfone, TTS local modular com PCM, ativação por nome mediante consentimento, consolidação semântica e resumos aprovados, análise automática de contradições e fundamentação, relatórios especializados, treinamento LoRA/QLoRA e refinamento visual. Nenhum treinamento de pesos acontece após conversas.
