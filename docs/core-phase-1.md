# Integração Core · etapa inicial independente · 2026-11-15

## Material efetivamente disponível

Repositório auditado: `dragonlisboa423-dev/nexora`, branch `feat/saly-smolin`, base `eb1d74e5580c2b513b16926f2381ff8a9e288ed3`. A consulta às branches publicadas encontrou essa branch, `feat/saly-intelligence` e `main`. Nenhuma continha `SALY_Pacote_Integracao_Codex_2026.zip`, `SALY_Core_v1/`, `CODEX_PROMPT_MASTER.md` ou `COMECE_AQUI.txt`. A busca no workspace também não encontrou o pacote.

O anexo `SALY_CORE_MEMORY_v1.json` foi baixado e lido integralmente: 34.851 bytes, SHA-256 `8e9ff45e4d8a9793454d9c0442f3180c377314b79fcb443bbb811847b613fcbc`. A cópia em `backend/core/data/` preserva os bytes originais. O manifesto registra a origem, a autorização explícita da solicitação, o adaptador e a ausência do pacote. O estado original `PROPOSTA_NAO_INSTALADA` permanece na semente; a ativação real fica separada em `app_config`.

**Não foi possível extrair o ZIP nem ler/executar o prompt mestre.** Esta etapa implementa requisitos independentes da mensagem e do JSON disponível. Não substitui nem afirma concluir uma fase especificada no documento ausente. Para alinhar as próximas etapas, é necessário anexar o ZIP ou publicar o arquivo e informar a branch/pasta.

## Auditoria e compatibilidade

| Área | Base inspecionada | Decisão desta etapa |
|---|---|---|
| Interface | React/TypeScript, Three.js/R3F, shaders, fallback 2D, estados de operações | Preservar núcleo, identidade, CSS e telas. Acrescentar Laboratório à Avaliação e evidências às respostas. |
| Backend/modelo | FastAPI, SSE OpenAI-compatible, modelo remoto configurável | Integrar política Core em cada geração, inclusive etapas do agente. Não alterar `.env`, modelo selecionado ou chave. |
| Memória | SQLAlchemy, SQLite/PostgreSQL, versões, correção, expiração, exclusão e proveniência | Preservar registros. Separar políticas estáveis das memórias pessoais. Testar reinício em processos independentes. |
| Autonomia | Registro tipado, autenticação, propostas e aprovações únicas | Manter barreiras. Adicionar somente verificadores locais de leitura/cálculo; nenhum shell, novo acesso externo ou contratação. |
| Smolin | Upload privado, parser isolado, original, páginas, busca lexical e encoder opcional | Preservar; retirar texto recuperado da mensagem de sistema e validar IDs de citações. Não declarar busca semântica sem encoder funcional. |
| Avaliação | Oito verificações locais e histórico | Preservar API e histórico antigos; separar novos relatórios por `kind=core-lab-v1` na mesma tabela. |
| Distribuição | PWA, cache público, Docker, HTTPS/Codespaces | Preservar; documentar instalação e teste em modo avião com os limites atuais. |

## Implementação

`backend/core/policy.py` valida o manifesto, SHA-256, schema e IDs únicos antes de ativar o Core. Apenas o arquivo incluído na distribuição é carregado; não existe instalação de políticas via chat, PDF ou ferramenta. O checksum detecta divergência do pacote revisado, não autentica um autor externo nem comprova a verdade do conteúdo.

A inicialização adiciona `core_active` e um histórico limitado de ativações em `app_config`. A operação é idempotente: reiniciar com a mesma versão não duplica ativação nem muda o epoch. Uma ativação nova incrementa o epoch para retirar contexto antigo de próximas gerações; conversas, originais, preferências e memórias existentes não são apagados. Não há alteração destrutiva de schema ou importação da semente como memória pessoal. O arquivo é carregado na inicialização; atualizar uma versão requer revisar o manifesto e reiniciar o backend.

O prompt recebe as 12 regras e prioridades compactadas a cada solicitação. Uma recuperação **lexical**, limitada a até duas áreas, fornece princípios científicos da semente, com origem, versão e hash. Isso não é pesquisa atual, embeddings semânticos ou treinamento de pesos. PDFs/memórias/princípios recuperados seguem como dados em mensagem separada de menor prioridade, nunca concatenados como novas instruções de sistema.

As ferramentas `check_load` e `check_energy_cost` fazem validação Pydantic e cálculo Decimal. Elas normalizam g/kg e W/kW, rejeitam unidades incompatíveis, valores não finitos, intervalos inválidos e campos extras. Capacidade é um limite de comparação; excedente em kg não vira litros. Os resultados representam os valores fornecidos, não medições ou uma certificação física. Os verificadores estão registrados no agente e disponíveis em **Ferramentas e integrações**; o código não obriga um modelo remoto a escolher a ferramenta nem garante que ele interprete corretamente qualquer enunciado.

Cada resposta concluída persiste uma evidência com versão/hash do Core, IDs de princípios recuperados, citações desconhecidas, IDs de execução e resultados de ferramentas determinísticas que de fato terminaram. A interface permite expandir esse registro. Propostas pendentes não são marcadas como executadas. Referências `[Core:...]` só são aceitas quando o princípio foi recuperado; `[Fonte:...]` mantém a validação de trechos existentes do Smolin. Isso comprova proveniência reconhecida, não a correção de toda frase. Nenhum raciocínio interno privado é solicitado ou exposto.

Ao excluir uma memória ou documento, a evidência também é retirada das respostas derivadas identificadas, para não manter dados numéricos privados nesse novo campo. Backups antigos continuam sendo cópias independentes, conforme a política de retenção já documentada.

## Laboratório SALY

Em **Avaliação → Laboratório SALY**, o botão **Executar testes locais · sem API** executa:

1. Leitura e verificação atual de integridade/schema do Core.
2. Soma de massas e comparação com capacidade: 15,7 kg, excedente 3,7 kg.
3. Energia/custo: 3 W × 24 h × 30 dias → 2,16 kWh e R$ 2,052.
4. Rejeição de litros como unidade de massa.
5. Rejeição de código pela calculadora limitada a aritmética.
6. Escrita, leitura e rollback de um registro técnico efêmero no banco atual.

O último teste não simula reinício nem testa armazenamento no telefone. A persistência após reinício foi verificada separadamente pela suíte em dois processos Python com banco temporário.

Os 16 casos de aceitação linguística do JSON são incluídos com entrada/esperado, mas ficam **inconclusivos / não executados no modelo**. Não há classificação por palavras-chave, respostas enlatadas ou nota falsa de inteligência. O relatório registra duração, timestamp, versões, observado, evidência, status e inventário dos recursos; pode ser exportado em JSON e reaparece após recarregar. O laboratório não chama o provedor, não envia documentos e registra `provider_requests=0`. Cotas e preços não são inferidos a partir da configuração.

Rotas novas, todas autenticadas: `GET /api/core`, `GET /api/laboratory`, `POST /api/laboratory`. Histórico anterior continua em `/api/evaluation`. O laboratório tem limite de cinco execuções por janela da limitação existente.

## Executar e verificar

No Codespaces, pare a instância anterior com Ctrl+C e use a mesma branch, ambiente virtual e configuração privada:

```bash
cd /workspaces/nexora
git pull --ff-only
npm --prefix frontend run build
SALY_SECURE_COOKIE=1 bash scripts/start.sh
```

Nenhuma dependência nova foi adicionada. Se for um ambiente novo, execute `bash scripts/install.sh` e configure o acesso privado como no README. Não recopie `.env.example` sobre um `.env` existente. Faça backup administrativo antes de atualizar dados reais, conforme `deployment.md`. O teste de um modelo real continua separado; pode consumir sua quota e não foi disparado nesta entrega.

Após desbloquear, abra **Avaliação**. Execute o laboratório, expanda os casos e exporte o relatório. Na tela **Ferramentas e integrações**, selecione `check_energy_cost` e use:

```json
{"power":{"value":3,"unit":"W"},"hours_per_day":24,"days":30,"tariff_brl_per_kwh":0.95}
```

Para carga:

```json
{"masses":[{"value":11.4,"unit":"kg"},{"value":2,"unit":"kg"},{"value":1.5,"unit":"kg"},{"value":0.8,"unit":"kg"}],"capacity":{"value":12,"unit":"kg"}}
```

Testes automatizados:

```bash
bash scripts/test.sh
.venv/bin/python scripts/browser_smoke.py
```

O segundo comando requer Playwright e Chromium já instalados conforme `backend/requirements-browser.txt` e a configuração de CI. Os testes criam dados e senha descartáveis, não usam credenciais reais. Em ambiente Codex, TestClient/Chromium podem precisar rodar fora do sandbox para comunicação local; isso não exige desativar TLS nem ampliar destinos de rede.

## Resultado e limitações

**97 testes Python passaram; 1 PostgreSQL foi pulado por falta de DSN descartável. Seis testes Vitest, TypeScript/Vite e Ruff passaram.** Chromium verificou laboratório/JSON/histórico, login, núcleo WebGL, microfone com dispositivo de teste, memória, Smolin, aprovações, calculadora, configurações, layout móvel, cache público e fallback offline, sem erros de página.

Os testes cobrem o fluxo da rota de chat com transporte controlado: política real → chamada estruturada → verificador determinístico → evidência persistida. Isso **não** comprova qualidade factual ou uso correto dessas novas ferramentas pelo modelo da conta da proprietária. Não havia chave de aplicação neste ambiente Codex; a conexão prévia mostrada no Codespaces não foi reexecutada aqui. Nenhuma API generativa ou serviço pago foi chamado para esta etapa.

As regras da semente são objetivos e orientações, não garantias universais. Consentimento/retenção de histórico, detecção ampla de conflitos e segredos, atualização de conhecimento, avaliação factual e robustez contra ataques continuam exigindo evolução. O histórico de conversas existente mantém sua política de armazenamento anterior; a integração do Core não o tornou automaticamente opcional nem criptografado. A memória tem banco real e passou no reinício controlado; isso não prova memória humana, consciência, AGI ou persistência garantida no ciclo de vida de uma hospedagem temporária.

## Próximas etapas e orçamento

| Dimensão | Estado após esta etapa | Dependência ou trabalho restante |
|---|---|---|
| Core modular do ZIP | Bloqueado por arquivo ausente | Receber pacote, ler prompt mestre inteiro, revisar módulos e adaptar sem executar scripts não inspecionados. |
| Core Memory JSON | Integrado parcialmente | Políticas, recuperação, verificadores e rastreabilidade reais; ampliação da avaliação, conflitos e retenção ainda pendente. |
| Voz própria | Não implementada | Escolher motor independente e voz pt-BR com licença adequada; testar síntese, arquivos e reprodução PCM com sincronização por áudio real. O catálogo atual usa o navegador. |
| Imagens | Não implementadas | Selecionar motor local compatível com hardware ou provedor com quota gratuita confirmada. Testar geração, edição, armazenamento e direitos de uso sem ativar cobrança. |
| Vídeos | Não implementados | Edição local por ferramenta apropriada e jobs verificáveis; geração exige modelo/hardware próprios ou quota autorizada. Exportação/cancelamento de vídeo ainda não existem. |
| Centro Smolin | Parcial | Fluxo lexical existente preservado; encoder semântico real, OCR e qualidade de extração ainda dependem de implementação/configuração/teste específico. |
| Android / PWA | Parcial | Manifesto/cache/layout existentes; testes físicos, persistência local e instalação verificada no telefone pendentes. Ver `android-offline.md`. |
| Offline completo | Não implementado | Banco local autorizado, limpeza/exportação/sincronização/conflitos, cache privado controlado e testes físicos. Inferência exige motor e pesos realmente funcionais no dispositivo. |
| Laboratório abrangente | Parcial | Seis verificações locais reais; testes de provedores, áudio físico, semântica, Android e desempenho sustentado ainda pendentes. |

Continuar dentro de R$ 0: primeiro alinhar o pacote, depois implementar dados locais/offline e edição local, avaliar hardware/licenças de voz e multimídia, conectar somente serviços cuja modalidade gratuita tenha sido confirmada. Cadastro de cartão, ativação de faturamento, contratação ou uso oneroso exigem autorização separada. Nenhuma chave, plano ou modelo instalado foi inventado.
