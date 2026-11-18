# SALY 2.0 — identidade botânica e experiência integrada

Etapa visual e estrutural sobre a SALY existente, a partir de `f03426b`. Especificação recebida e lida integralmente em **17/11/2026, America/Sao_Paulo**. A auditoria anterior às alterações está em [`SALY_2_VISUAL_AUDIT.md`](SALY_2_VISUAL_AUDIT.md).

Não se reconstruiu a aplicação. Chat/Groq, Core Memory/RAG, arquivos originais, memórias, preferências, catálogo de voz, agenda, alarmes, biblioteca e cofre continuam nos mecanismos anteriores. `.env`, chaves, DSN e modelos não foram alterados. Nenhum serviço pago, inferência remota ou geração externa foi acionado para esta etapa.

## 1. Auditoria e preservação

Foram inspecionados `main.tsx`, `Core.tsx`, os shaders/R3F, os painéis, Biblioteca/BookBlocks/Editor, Compras/Espaço, Estúdio/FFmpeg, leitores PDF/EPUB, armazenamento e APIs pessoais/PWA. A base tinha cerca de quinze destinos principais, muitos controles técnicos antes das funções de criação e uma esfera procedural fluida. Boa parte das funções já era real e foi reaproveitada.

A estratégia de dados é **aditiva**. Não houve migração destrutiva nem substituição de banco. As metas manuais usam uma chave nova em `app_config`; fotos de produto usam os assets privados existentes com vínculo próprio. Comprovantes, IDs, revisões, permissões e backups continuam válidos. A revisão de uma compra mantém ambas as imagens; sua exclusão remove os dois assets e mantém as regras existentes dos alarmes.

## 2. Quatro áreas e navegação

| Área | Entrada | Acessos preservados |
|---|---|---|
| Conversa | `/` | Núcleo, mensagem, microfone/modo de voz, histórico em gaveta, contexto e aprovações reais. |
| Conhecimento | `/knowledge` | Centro Memorial, `/memory`, `/knowledge/documents`, `/library`, `/space` e preferências. |
| Mídia | `/studio` (`/media` redireciona) | Imagem, vídeo, galeria, produções, arquivos/downloads e cancelamento reais. |
| Rotina | `/routine` | `/agenda`, `/alarms`, `/purchases`; orçamento, desejos, fotos e metas manuais. |
| Ajustes — acesso secundário | `/advanced` | Preferências, privacidade, vozes, conexão, ferramentas, Laboratório, Avaliação e cofre. |

O menu principal possui quatro destinos. No telefone há uma barra inferior de quatro áreas e menu secundário. A navegação contextual evita repetir todos os módulos em toda tela. O histórico usa um `dialog` nativo, com fechamento por Escape e foco do navegador; não ocupa permanentemente a tela. A abertura de uma conversa conserva o carregamento anterior e retorna à área de conversa.

A mudança intencional de URL é a entrada `/knowledge`: agora abre o Centro Memorial; o acervo Smolin está a um clique em `/knowledge/documents`. As APIs `/api/knowledge`, IDs, originais e links de citação não mudaram. Os leitores `/knowledge/:id/read` e `/knowledge/:id/text` continuam acessíveis. Não há exclusão de documentos para reorganizar a navegação.

Ferramentas/argumentos JSON, diagnóstico e opções de provedores ficam fora da navegação principal. Atividades continuam acessíveis pela Rotina; Avaliação e Laboratório, por Ajustes e pelas URLs antigas. Não se retiraram recursos internos do agente.

## 3. Coração vegetal e identidade

`Core.tsx` preserva a interface de estados/sinal do motor anterior e agora carrega `BotanicalCanvas.tsx` sob demanda. A deformação procedural original evolui sobre geometria própria em `botanical_geometry.ts`: tecido central lobado, folhas curvas sobrepostas, nervuras ramificadas e raízes tubulares. Não se usa uma esfera com decoração, ícone cardíaco humano, modelo estático importado, toros/circuitos ou nova biblioteca gráfica.

- **Repouso:** pulsação estética discreta e flexão dos tecidos.
- **Escuta:** expansão/luz respondem ao RMS real do microfone, somente quando a captura está ativa.
- **Processamento:** luz percorre nervuras enquanto os estados reais de busca, transcrição, síntese ou execução estão ativos.
- **Resposta/voz:** tokens e eventos de fala mantêm seus estados anteriores; PCM do motor local fornece amplitude real. Voz do navegador continua usando eventos, sem inventar um sinal PCM que esse serviço não fornece.
- **Erro:** tonalidade discretamente mais quente; texto de estado/alerta permanece explícito. A animação não comprova raciocínio nem conclusão de ferramenta.

O órgão é uma anatomia vegetal **fictícia**, não uma alegação de vida biológica, consciência ou medição fisiológica. O clock, a suavização de energia e o fluxo de eventos existentes foram reaproveitados. A alternativa vetorial botânica mantém acesso sem WebGL. A perda de contexto GL troca a cena por essa alternativa; não se promete recuperação automática do driver. Rótulos acessíveis de estado estão em português.

O sistema global usa fundo florestal `#0c1510`, superfícies orgânicas, verde-folha, tipografia serifada editorial com fontes locais do sistema e transparência moderada. O estilo foi estendido ao login, páginas de leitura e cofre. Ícones PWA 192/512 são próprios, reproduzíveis por geometria local, sem imagens/fontes externas. Manifesto e cor da barra do navegador acompanham a identidade; o ID/scope da PWA não mudou.

## 4. Experiências funcionais

### Biblioteca

Foram reaproveitados os documentos, `BookBlocks`, editor e controles científicos. Capas ganharam espinha visual, proporção editorial e páginas em papel claro; livros permanecem rascunhos ou edições publicadas conforme seus metadados reais. Publicação/revisão não foi simulada. Opções de autoria ficam em **Opções do livro**, e a narração em um controle contextual.

Há páginas duplas/simples responsivas, efeito CSS de virada em perspectiva, botões, setas e **deslize horizontal real**. Scroll vertical, seleção de texto, campos e controles científicos são preservados. Gestos curtos, verticais, longos ou originados nos controles não viram páginas. Sumário, marcadores, notas, conclusão e retomada continuam persistentes. A fila de progresso foi associada à sessão do livro para não perder a gravação ao sair rapidamente; a atribuição do ID após criar um livro foi corrigida e testada.

O mesmo controle de gesto atende o leitor PDF original e a leitura textual. PDFs mantêm canvas/camada de texto, figuras, download e checksum originais. EPUB/TXT/DOCX preservam a alternativa textual por seções/capítulos; **não se declara que todo formato foi convertido em páginas físicas nem que a diagramação original EPUB/Word é integralmente reproduzida**. A virada é uma transição de interface, não uma simulação física de papel. O modo vertical acessível e movimento reduzido não têm animação de virada.

O livro de Biologia e suas fontes/conteúdos não foram reescritos. O teste compara os capítulos antes/depois da leitura, além de exercitar quiz, gráfico logístico, DNA/RNA, células e microscópio didático. Isso preserva o livro existente; não certifica uma edição científica completa ou calibração de microscópio.

### Compras, desejos e finanças

`PurchaseDashboard.tsx` mostra cartões com fotos fornecidas pela pessoa, categorias, distribuição de gastos, últimos seis meses registrados, orçamento e saldo **do orçamento**. Todos os valores vêm dos registros existentes. Desejos, planejamentos e cancelamentos continuam excluídos dos gastos realizados segundo a regra anterior. Sem orçamento, aparece **A definir**; sem registros, há orientação para começar, sem dados fictícios.

- Foto do produto: vínculo `product_image_id` próprio, separado de `image_id` do comprovante. PNG/JPEG/WebP estáticos, até 8 MiB/16 MP, normalização privada sem metadados. Sem busca externa de fotos ou inferência de preço a partir da imagem.
- Metas: valores manualmente informados, em centavos inteiros, com confirmação e revisão. Até trinta metas em `purchase_savings_goals`; atualizar/remover exige revisão vigente. A barra reflete reservado/meta, não transferência bancária. Reservar numa meta não altera silenciosamente o orçamento.
- Cadastros, conferência do total, frete/desconto, datas, comprovantes e alertas anteriores continuam disponíveis. O orçamento detalhado fica recolhido até solicitado. Exportação preserva os valores e inclui as metas; não exporta ponteiros inválidos para imagens privadas.
- Fotos continuam privadas, fora do cache público. Metas/fotos não são copiadas automaticamente ao cofre; a sincronização anterior de compras escolhidas foi preservada.

Não foram inventados saldo bancário, rendimentos, comparações de preço ou dados financeiros. Os valores das capturas de teste pertencem a bancos descartáveis e não são inseridos na conta da usuária.

### Mídia

O Estúdio tem abas **Imagem, Vídeo, Galeria e Produções**, com navegação de teclado, prévias dos arquivos reais e controles preservados. A edição cria uma imagem nova, atualiza a prévia e mantém a original. A montagem mostra cenas/miniaturas e continua exportando com FFmpeg; sua fila/progresso/cancelamento/download/checksum aparecem em Produções. Galeria e resultados não são mockups.

Configuração, modelos, disponibilidade e limites ficam em `/advanced/media`. Sem provedor, a geração aparece desativada. Configuração detectada ainda é identificada como necessitando teste; não é chamada de geração certificada. Vídeo por IA continua não conectado; a montagem local não se apresenta como criação de cenas por um modelo. Nenhuma credencial foi criada/exposta nem chamada paga habilitada.

### Centro Memorial

É a organização visual conjunta de memórias pessoais, acervo documental, livros e referências, com origem e controles próprios. Não se fundiram as tabelas nem se converteram documentos em instruções pessoais. Consentimento, edição/exclusão e tratamento de conteúdo não confiável permanecem. Não se afirma que memória automática, autonomia ou uma nova integração cognitiva foram concluídas nesta etapa.

## 5. Desempenho, acessibilidade e PWA

- A qualidade automática/padrão usa três folhas e geometria combinada: **8 chamadas de desenho, 4.200 triângulos** observados no cenário padrão. Qualidade alta conserva mais detalhe; não se afirma que ela tem o mesmo custo.
- A primeira versão com tecido mais denso mediu aproximadamente 40 quadros/s no Chromium por software. A redução/composição de geometria e passagens de transparência devolveu aproximadamente 60 quadros/s ao padrão.
- Antes: 151 frames em 2.500,5 ms (~60,39 fps). Depois da otimização: 151 em 2.502,8 ms (~60,33 fps), com média do frame próxima de 16,9 ms. São **amostras curtas de um ambiente**, não benchmark de Android ou garantia em 8 GB. O JS observado na página permaneceu na ordem de 1,3 MB, incluindo a biblioteca Three existente; o chunk 3D é separado da alternativa vetorial. Precache do service worker é um fluxo público separado dessas entradas de Resource Timing.
- O render pausa quando a cena sai da tela ou a página é ocultada; movimento reduzido usa render sob demanda e remove animações decorativas. Telemetria DOM vem de frames/renderização reais, não de números pré-programados.
- Core/cena 3D, áreas e módulos continuam sob demanda; imagens da galeria/cartões usam carregamento preguiçoso. O Estúdio evita polling em aba oculta. Não se adicionaram bibliotecas de gráficos, fontes remotas, pós-processamento pesado ou modelos.
- Contraste, foco, rótulos em português, navegação por teclado, modo vertical e alvos principais de toque foram revisados. Não se declara certificação WCAG completa, acessibilidade com todo leitor de tela ou equivalência a um teste em Android físico.
- PWA/cofre continuam no mesmo endereço/ID. O cache é só de recursos públicos; a versão agora também considera manifesto, HTML e ícones para não manter a identidade antiga após uma atualização desses arquivos. APIs e arquivos privados ficam fora do cache público. Dados locais continuam cifrados no mecanismo anterior.

Não foi gerado APK. A instalação Android continua por Chrome/PWA em HTTPS. Instalar a interface não hospeda backend/Groq no telefone e não cria inferência offline. Leia `INSTALAR_SALY_ANDROID.md` e `android-offline.md` para os limites anteriores, que continuam válidos.

## 6. Arquivos e validação

| Etapa | Arquivos principais |
|---|---|
| Auditoria | `docs/SALY_2_VISUAL_AUDIT.md` |
| Navegação | `main.tsx`, `navigation.ts`, `Areas.tsx`, `state_labels.ts` |
| Identidade | `Core.tsx`, `BotanicalCanvas.tsx`, `botanical_geometry.ts`, `botanical.css`, ícones/manifesto/HTML, `generate_icons.py` |
| Biblioteca | `Library.tsx`, `page_swipe.ts`, `PdfBook.tsx`, `TextBook.tsx` |
| Compras | `Personal.tsx`, `PurchaseDashboard.tsx`, `finance.ts`, `purchase_visual.py`, ajustes aditivos em `personal.py`/`main.py` |
| Conhecimento/Mídia | `Panels.tsx`, `Areas.tsx`, `Studio.tsx` |
| Otimização/PWA | módulos do núcleo, estilos responsivos, `vite.config.ts` |
| Verificação | `test_visual_purchases.py`, `botanical.test.ts`, `browser_visual_2.py`, helper de navegação e regressões existentes |

Os resultados finais estão em [`SALY_TEST_REPORT.md`](SALY_TEST_REPORT.md). Os testes de navegador usam bancos descartáveis e transportes controlados quando precisam testar chat/reconhecimento. Arquivos, renderização, microfone de teste, operações SQL, FFmpeg, reprodução e criptografia são reais; isso não certifica inferência remota/ASR físico/naturalidade da voz.

```bash
.venv/bin/python -m pytest -q
npm --prefix frontend test
npm --prefix frontend run build
.venv/bin/python scripts/browser_visual_2.py
.venv/bin/python scripts/browser_library.py
.venv/bin/python scripts/browser_biology.py
.venv/bin/python scripts/browser_personal.py
.venv/bin/python scripts/browser_studio.py
.venv/bin/python scripts/browser_planning.py
.venv/bin/python scripts/browser_smolin_files.py
.venv/bin/python scripts/browser_voice.py
.venv/bin/python scripts/browser_smoke.py
.venv/bin/python scripts/browser_offline.py
.venv/bin/python scripts/browser_books_offline.py
.venv/bin/python scripts/browser_intelligent_library.py
```

Os testes antigos foram adaptados à navegação de quatro áreas e às divulgações/abas explícitas; suas verificações de dados, publicação, cálculo, arquivos, checksum e permissões foram mantidas. A resposta HTML de proxy é injetada em contexto com service worker bloqueado para a interceptação ser confiável; PWA e cache privado são testados separadamente. Isso não é um diagnóstico do proxy do Codespace da usuária.

## 7. Atualizar com segurança

Faça backup privado pelo procedimento já existente e pare o servidor antes de atualizar. Não apague banco/cofre nem recrie a senha. No Codespace, na branch de desenvolvimento:

```bash
cd /workspaces/nexora
git fetch origin
git switch feat/saly-smolin
git pull --ff-only
bash scripts/install.sh
SALY_SECURE_COOKIE=1 bash scripts/start.sh
```

O frontend precisa ser recompilado; `start.sh` sozinho não recompila. Se a PWA avisar nova versão, guarde o que estiver digitando e use **Atualizar agora**. Banco, memórias, arquivos e configurações permanecem no armazenamento anterior. O ícone instalado depende também da atualização de manifesto do Chrome; não se promete atualização instantânea do atalho Android.

Limites remanescentes: Android físico/GPU real e fala física não certificados; qualidade alta pode custar mais; EPUB/Word seguem alternativa textual quando a diagramação original não é reproduzível; criação generativa depende do provedor anterior e continua desativada sem configuração/teste. A segunda etapa de inteligência, memorização contextual e autonomia não foi antecipada por esta reformulação.
