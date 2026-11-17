# Biblioteca, inteligência documental, voz e Android — evolução da SALY existente

Especificação recebida em `Texto colado.txt` (8.342 bytes), lida integralmente. Base auditada: `d65bdbb`, branch `feat/saly-smolin`. Nenhuma reconstrução da interface, alteração de `.env`, troca do modelo Groq, senha, memória ou integração existente. Não se adicionou serviço pago.

## Fase 1 — diagnóstico anterior às alterações

A arquitetura é React 19/TypeScript/Vite com núcleo Three/R3F; backend FastAPI e SQLAlchemy; SQLite/FTS5 no desenvolvimento e PostgreSQL/pgvector preparado para implantação. `backend/llm/provider.py` mantém a integração OpenAI-compatible/Groq, streaming e ferramentas tipadas. `main.py` recupera até oito trechos e envia conteúdo limitado por trecho; não envia livros inteiros. Memórias, conversas e originais são persistidos no banco privado. Autenticação é da proprietária; não há cadastro público.

O Smolin já preservava originais, removia duplicatas por SHA-256, aceitava vários formatos, processava em subprocessos isolados, tinha envio em blocos de 2 MiB e leitor PDF.js do original. Limites padrão: 64 MiB por arquivo, 200 MiB de acervo, cinquenta documentos, dois milhões de caracteres extraídos por documento. `SALY_MAX_PAGES` existente é respeitado; default do parser é 2.000. Uma configuração antiga de 500 continua valendo. Não foram apagados arquivos para aumentar capacidade.

Lacunas encontradas: a interface descartava temporários após falha e não expunha retomada; não existia GET de sessão de upload. A extração/indexação não tinha checkpoint reutilizável. Listagens e verificação de quota carregavam textos de toda a coleção. EPUB era lido na ordem dos nomes, não do spine. Erros de extração eram genéricos. O OCR existente atendia imagens/quadros, não PDFs. Havia busca lexical e contrato remoto de encoder, mas nenhum encoder remoto configurado ou semanticidade local. Não havia mapa documental. A voz preenchia o campo de texto, sem completar o ciclo por ativação. A PWA e o cofre criptografado já funcionavam para dados/documentos escolhidos, configurações, livros e agenda; faltava cópia escolhida de conversas.

O erro antigo `Unexpected token '<'` comprova uma resposta HTML interpretada como JSON, mas não comprova sua causa no proxy do Codespace. O tratamento anterior de respostas inesperadas e os blocos foram preservados. Arquivo protegido, corrompido, acima do limite ou dependência ausente continuam sendo possibilidades distintas. Nesta rodada, o navegador encontrou e reproduziu outra falha: a API de posição de leitura aceitava só PDF; foi corrigida para o leitor textual EPUB.

A ordem executada segue diagnóstico → importação/leitura → recuperação/citações → mapa → voz → experiência móvel. Os módulos existentes continuam responsáveis por suas funções; os novos se integram ao fluxo real.

## Fase 2 — importação, leitura e processamento

- `catalog.py` projeta metadados no SQL, sem materializar páginas/textos de todos os livros para listar o acervo ou verificar quota. Texto só é carregado para um documento/consulta limitada.
- Transferências grandes preservam blocos confirmados após pausa/falha e recarga da página. A retomada pede o mesmo arquivo e valida SHA-256 de **cada bloco já confirmado**, um bloco por vez. Não é possível comprovar os bytes ainda não enviados antes de recebê-los. Originais completos continuam tendo SHA-256 integral e deduplicação. Transferências expiram após 24 horas; não são retomadas depois de excluídas/expiradas.
- Pausa em um envio pequeno, feito em uma requisição única, não é oferecida como retomada em blocos. Cancelar/descartar continua explícito.
- Extração concluída gera checkpoint privado por job. Página indexada, fragmentos e cursor são confirmados na mesma transação. Pausa/cancelamento interrompem o processo; retomada/reinício reutilizam a extração e pulam páginas já confirmadas. Se a interrupção ocorreu **durante a extração**, essa etapa é refeita: não se promete checkpoint dentro do parser/OCR de cada página. Worker de aplicação único; `SALY_DOC_WORKERS` permite um ou dois parsers concorrentes, sem fila distribuída.
- Erros aparecem com recuperação por retomada/reprocessamento. PDFs protegidos, excesso de páginas e arquivos incompatíveis têm causas específicas quando detectadas. O original permanece disponível mesmo após falha de interpretação.
- EPUB respeita OPF/spine e recupera título, autor e rótulos de capítulos quando presentes. Pacotes simplificados sem container usam ordem de arquivos com aviso; não se presume que isso reproduz um EPUB completo. Referências externas, entidades XML e expansão ZIP excessiva são recusadas. EPUB enviado não executa scripts nem busca recursos na rede.
- O leitor textual oferece capítulos/seções e posição persistente para EPUB/TXT/Markdown/DOCX e formatos compatíveis. **É texto extraído**, sem alegação de conservar toda a diagramação EPUB/Word. PDFs continuam no leitor original PDF.js, sem substituir desenhos por texto reconstruído. O parser PDF recupera capítulos do sumário quando disponíveis.
- OCR de PDF é opcional e solicitado por botão, com aviso de CPU. Requer Poppler `pdftoppm` e Tesseract, processa uma imagem por vez, preserva páginas textuais e identifica as páginas OCR. Até quarenta páginas por operação, além dos tetos de CPU/memória/tempo; isso não garante que qualquer PDF de quarenta páginas caiba no tempo. Textos OCR podem conter erros.

Instalação opcional dos motores gratuitos no servidor:

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-por ffmpeg
```

No ambiente de teste já havia Poppler, FFmpeg e Tesseract. OCR real foi testado em inglês, o idioma disponível aqui; português requer o pacote de idioma. Não foi instalado modelo generativo.

## Fase 3 — recuperação e RAG com fontes

`intelligence.py` adiciona **LSA local real**: TF-IDF, projeção por SVD truncada e similaridade cosseno. Os componentes/vocabulário/vetores são aprendidos no próprio acervo e persistidos em arquivo privado NPZ, sem pickle. Não são vetores aleatórios usados como substituto de embeddings. A projeção aleatória determinística só acelera a aproximação da SVD. Mudanças no conjunto de fragmentos invalidam a assinatura do índice; exclusão também remove o arquivo derivado.

O índice local é construído/reconstruído sob demanda na consulta, em thread e com um lock, usando no máximo mil fragmentos e seis mil termos, dimensão de até 24 componentes. A primeira consulta pode demorar mais; a indexação textual é automática na importação. São necessárias pelo menos três unidades textuais e vocabulário suficiente. O mapa/status informam cobertura parcial. **LSA aprende associações estatísticas da coleção; não é encoder neural multilíngue e não garante relevância ou sinônimos gerais.** Documentos além da cobertura LSA continuam na busca textual. Não se alega suporte semântico ilimitado a uma biblioteca inteira.

Pode ser desabilitado com `SALY_LOCAL_LSA=0`. O contrato existente de encoder remoto de 384 dimensões/revisão imutável continua separado, dependente de configuração e consentimento; nenhum serviço remoto foi ativado. Busca por livro aplica filtro documental antes do ranking lexical/local. Resultados LSA são marcados `retrieval=local_lsa`, com score, e não substituem correspondências textuais. Não se enviam os índices para o Groq.

O chat e as ferramentas usam a recuperação existente, agora enriquecida com autor/título/capítulo/rótulo quando disponíveis e referências reais a documento/página/tempo. O contexto por trecho é limitado. A política manda distinguir evidência de inferência e admitir contexto insuficiente; o verificador existente rejeita IDs de citação desconhecidos. Isso **não certifica automaticamente a fidelidade factual ou a interpretação da resposta**. As chaves e o modelo do usuário foram preservados, sem consumir inferência externa nesta verificação.

## Fase 4 — mapa de conhecimento

No Centro Smolin, expanda **Mapa de conhecimento com fontes**. Há grafo SVG, zoom, seleção por clique/teclado, lista acessível, filtro e trechos/links originais. Termos normalizados são extraídos do texto real; conexões registram sua coocorrência nos mesmos fragmentos. Um termo pode reunir fontes de livros diferentes. Atualizar o mapa consulta o índice atual após novas importações, sem reconstruir uma falsa árvore científica fixa.

Limites: mil fragmentos examinados, sessenta conceitos e 150 conexões, explicitados na resposta. O mapa não mantém livros inteiros em memória. Relações são `documented_cooccurrence`, **não causalidade nem concordância científica comprovada**. Fontes de autores diferentes que contenham marcadores explícitos de contraste podem formar candidatos `contrast_candidate`; o aviso exige revisão humana. Não se declara divergência confirmada nem se gera hipótese por IA sem fonte. O detector é textual e limitado; não é uma revisão científica automatizada. Nenhum retreinamento do Groq ocorreu.

## Fase 5 — conversa por voz em primeiro plano

Na visão central, use **Modo de voz SALY**, após autorizar o provedor remoto nas configurações. O botão informa que o reconhecimento do navegador pode enviar áudio ao fornecedor. Diga “SALY”/“Sali” e o comando; após a resposta falada, existe uma janela de trinta segundos para novas perguntas sem repetir o nome. Apenas resultados finais são enviados, evitando submissões por cada hipótese intermediária.

Durante geração/síntese/fala, o microfone fica desligado. Depois do fim real do áudio, ele pode reabrir enquanto o modo estiver ativo e visível. Há botão para desligar o modo, interrupção, controles de reprodução existentes e comando “desligar microfone” dentro da sessão. Troca de rota, página oculta ou erro desligam o modo; tracks e reconhecimento são encerrados. Permissões e HTTPS são necessários. Navegadores podem interromper reconhecimento, negar autoplay ou não fornecer SpeechRecognition; nesses casos a interface indica indisponibilidade. Não se promete escuta com app fechado/tela bloqueada nem processamento contínuo em segundo plano no Android.

A resposta usa a voz selecionada no catálogo existente. eSpeak feminino pt-BR pode sintetizar WAV real no servidor e animação usa PCM, mas tem timbre sintético. Vozes do navegador variam conforme dispositivo. **Voz feminina neural natural/exclusiva permanece bloqueada por falta de um motor/modelo licenciado instalado e validado**; não se chama eSpeak de voz natural nem se troca o modelo do usuário. A transcrição Whisper de arquivos continua opcional e com a limitação de download documentada em `SMOLIN_FILES_AND_PDF.md`; SpeechRecognition do modo de voz não é Whisper local.

## Fase 6 — PWA, Android e acesso sem internet

Manifesto, ícones, instalação pelo Chrome e service worker com cache versionado de arquivos públicos foram preservados. APIs, conversas, PDFs e chaves **não** entram no cache público. Falha de preparação do service worker agora aparece em aviso, em vez de ser silenciosa. Uma atualização é aplicada por ação explícita da usuária.

O cofre IndexedDB/AES-GCM existente continua oferecendo documentos e livros escolhidos, configurações de consulta e dados autorizados; sua solicitação de persistência ao navegador, limites, tratamento de falhas e conflitos foram mantidos. A nova aba **Histórico guardado** copia conversas escolhidas para o cofre cifrado: até dez conversas, últimas cem mensagens, até 1 MB por conversa. São cópias de consulta, sem ferramentas/credenciais do servidor e sem reenvio/sincronização ao histórico remoto. Exclusão local requer confirmação. Cópias antigas e backups permanecem até remoção local; não há alegação de replicação automática do histórico.

Instalação: abra a URL HTTPS da aplicação no Chrome Android → ⋮ → Instalar aplicativo/Adicionar à tela inicial, quando disponível. Isso instala a interface PWA, **não hospeda o backend no telefone**. Codespace/servidor deve permanecer acessível para Groq e processamento. Não foi gerado APK/Capacitor nem certificada instalação física nesta rodada.

Teste manual em modo avião: abra `/offline` online, prepare/desbloqueie o cofre, escolha os documentos/livros/conversas e confirme que foram guardados; desligue a internet, recarregue, desbloqueie e consulte os dados locais. Cópia de conversa, configurações e documentos não possibilita respostas de IA offline. Não há modelo generativo local certificado. Para publicação HTTPS e instalação, consulte também `INSTALAR_SALY_ANDROID.md` e `deployment.md`.

## Verificação e próximos limites

Os resultados finais desta rodada são registrados em `SALY_TEST_REPORT.md`. Testes novos cobrem EPUB/spine, scripts não executados, blocos verificados após reabrir o banco, cursor/checkpoint sem repetir parser, pausa/retomada, busca por livro, associação LSA sem termo literal, fontes entre livros, exclusão dos índices, OCR de PDF e snapshot privado/bounded de histórico. Chromium complementa importação múltipla, leitor real, retomada, mapa, estados de voz e cofre offline. Reconhecimento/chat controlados em testes **não comprovam acurácia ASR nem inferência Groq real**.

```bash
.venv/bin/python -m pytest -q
npm --prefix frontend test
npm --prefix frontend run build
.venv/bin/python scripts/browser_intelligent_library.py
.venv/bin/python scripts/browser_smolin_files.py
.venv/bin/python scripts/browser_smoke.py
.venv/bin/python scripts/browser_offline.py
.venv/bin/python scripts/browser_voice.py
```

Próximos bloqueios, sem substituição visual enganosa: encoder neural local de qualidade com pesos/licença/download verificáveis; avaliação científica das relações e da fidelidade RAG; OCR com checkpoint por página/limites maiores; naturalidade de voz neural e transcrição local efetivamente instaladas; validação no Android físico e escala de coleções maiores. Os recursos atuais são progressivos e limitados, não uma alegação de conclusão irrestrita de todos esses critérios.

Atualização no Codespace, com backup privado antes e servidor parado, sem apagar banco:

```bash
cd /workspaces/nexora
git fetch origin
git switch feat/saly-smolin
git pull --ff-only
bash scripts/install.sh
SALY_SECURE_COOKIE=1 bash scripts/start.sh
```

### Arquivos por fase e resultado final

| Fase | Arquivos principais criados/alterados | Resultado |
|---|---|---|
| 1 — diagnóstico/correções | `catalog.py`, `service.py`, `extract.py`, `Smolin.tsx`, `main.py` | Metadados sem carregar toda a coleção; causas de falha e resposta sem fontes explícitas. |
| 2 — biblioteca | `uploads.py`, `library_api.py`, `formats.py`, `ocr_pdf.py`, `TextBook.tsx` | Blocos verificáveis/retomada, checkpoint, spine/autor/capítulos, leitor textual e OCR opcional reais. PDF original preservado. |
| 3 — inteligência documental | `intelligence.py`, `service.py`, `main.py`, `laboratory.py`, `.env.example` | LSA estatística local integrada à recuperação do chat; filtro por livro e metadados de fonte; encoder neural não instalado. |
| 4 — mapa | `KnowledgeMap.tsx`, `intelligence.py`, `style.css` | Coocorrência com fontes, seleção/zoom/teclado e candidatos de contraste a revisar; sem causalidade inventada. |
| 5 — voz | `voice_command.ts`, `audio.ts`, `main.tsx`, `operations.ts` | Ativação/janela, envio de resultados finais, resposta falada com motor disponível, desligamento/permissões. Naturalidade neural pendente. |
| 6 — móvel/offline | `pwa.tsx`, `offline/OfflineHistory.tsx`, `offline/OfflineWorkspace.tsx`, `offline/vault.ts` | PWA/cofre existentes preservados; histórico escolhido cifrado e consultável offline; Android físico/APK não certificados. |
| Verificação/guia | `test_smolin_library.py`, `voice_command.test.ts`, `browser_intelligent_library.py`, `browser_smoke.py`, `README.md`, este guia e relatório de testes | 156 Python passaram, 1 PostgreSQL pulado, 17 Vitest, build e cinco fluxos Chromium passaram. |

O arquivo `.env` do servidor não foi alterado. A síntese local para testes usa o runtime eSpeak existente em `.tools` quando não há binário no sistema; nenhuma instalação de modelo neural foi presumida. Um servidor sem eSpeak configurado continua indicando indisponibilidade no catálogo. Todos os novos módulos se integram à aplicação existente; não constituem uma biblioteca de demonstração separada.
