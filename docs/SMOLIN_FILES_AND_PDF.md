# Centro Smolin: arquivos, mídia e PDF original

Atualização de 2026-11-16, sobre a SALY existente. O escopo é upload/download do Centro Smolin, interpretação de arquivos e leitor de PDF. Interface principal, configuração Groq, conversas e demais módulos foram preservados.

## Android: confirmação antes de atualizar

A SALY já possui manifesto, ícones e service worker para instalação como **PWA pelo Chrome Android**, com a mesma interface do site. Abra a URL HTTPS da aplicação, faça o login privado e use **⋮ → Instalar aplicativo / Adicionar à tela inicial**, quando oferecido. Isso não hospeda o servidor dentro do celular: Codespaces/hospedagem continuam necessários para IA, acervo e processamento online. O cofre anterior oferece cópias offline autorizadas; não torna o Groq offline. Nenhum APK foi gerado e nenhuma instalação em Android físico foi certificada nesta rodada.

## Guardar e baixar é diferente de interpretar

Todos os formatos podem ser guardados como originais privados, dentro dos limites de tamanho/acervo. Tipos sem interpretador ficam em `stored_only`, com download e mensagem explícita. Um nome `.txt` com conteúdo binário inválido ou um falso PDF pode ser recusado por inconsistência; não se executam programas para “interpretá-los”.

| Formato | Capacidade atual |
|---|---|
| PDF | Original intacto; extração de camada textual por página e leitor visual do PDF original. PDF escaneado sem camada textual continua exigindo OCR de PDF separado, ainda não implementado. |
| TXT, Markdown, CSV/TSV, JSON/JSONL, XML, código, legendas SRT/VTT e outros textos | Texto UTF-8 ou UTF-16 com BOM, sem executar scripts/consultas. JSON/código são conteúdo textual, não políticas ou ferramentas. |
| HTML/SVG textual | Texto visível; scripts/estilos são ignorados. Não se executa HTML enviado. |
| DOCX, XLSX, PPTX, ODT/ODS/ODP | Extração de texto/planilhas/slides em ZIP limitado. Fórmulas não são recalculadas e macros não são executadas. Diagramação original permanece no download, sem promessa de conversão perfeita. |
| EPUB | Texto das seções HTML; ordem dos arquivos explicitamente declarada, sem prometer reproduzir toda a paginação/spine do EPUB. |
| ZIP | Índice de nomes dos arquivos, sem executar/extrair seu conteúdo arbitrário no servidor. Há limites de expansão e entidades XML são rejeitadas. |
| PNG/JPEG/WebP/BMP/TIFF/GIF estático | OCR local com Tesseract, se instalado, limitado à imagem/quadro inicial. Não é descrição visual geral nem análise de todos os quadros de um GIF/TIFF. O original permanece intacto. |
| MP3/WAV/FLAC/Ogg/M4A e MP4/WebM | Metadados reais por FFprobe e reprodução nativa quando o codec é suportado no navegador. Vídeos têm até seis quadros amostrados com OCR e citações de tempo. Fala exige o motor de transcrição abaixo. |
| Outros binários, executáveis, formatos proprietários | Armazenamento/download, sem execução e sem alegação de interpretação. |

Somente texto efetivamente extraído entra na busca e no contexto do agente. Resultados de vídeo/transcrição incluem `start_seconds`, `end_seconds` e método; links usam `#t=`. Metadados, silêncio ou OCR vazio não viram uma compreensão inventada da mídia. O agente recebe os estados/limites do arquivo e mantém as permissões existentes de conhecimento/consentimento remoto.

## Erro HTML/JSON e arquivos grandes

O print mostra HTML sendo passado a `JSON.parse`; sozinho, não identifica se a origem era sessão, proxy ou limite de corpo. O cliente agora reconhece respostas inesperadas e HTTP 413, sem exibir erro bruto “Unexpected token” ou tratar HTML como recebimento bem-sucedido.

O limite padrão do Smolin passou a **64 MiB**, separado do limite geral de outros uploads. Acima de 4 MiB, o cliente envia blocos de **2 MiB**, confirmando posições no servidor. Reenvio do mesmo bloco é idempotente; posições/conteúdo divergentes e conclusão incompleta são rejeitados. Originais, metadados e job são gravados na mesma transação. Cancelamento remove o temporário; transferências abandonadas expiram em 24 horas e são limpas no próximo início de envio. Há no máximo três transferências simultâneas e reserva de capacidade com o acervo.

Limites configuráveis, sem sobrescrever seu `.env`:

```dotenv
SALY_SMOLIN_MAX_UPLOAD_MB=64
SALY_MAX_TOTAL_MB=200
SALY_MAX_DOCUMENTS=50
SALY_MAX_PAGES=2000
```

`SALY_MAX_PAGES` existente é respeitado; se seu `.env` ainda define 500, esse é o teto de extração textual. O leitor visual abre o original independentemente do sucesso da extração. Arquivos inválidos/protegidos ou limites de processamento podem impedir interpretação; o original confirmado permanece para download. O teto de upload configurável é limitado a 512 MiB; isso não garante espaço ou memória da hospedagem. Upload em blocos evita limites de corpo de uma requisição grande, mas não contorna autenticação ou políticas do proxy.

Downloads têm sessão obrigatória, `nosniff`, `no-store`, nome UTF-8 e suporte a `Range`/206. Tipos não apropriados para exibição são enviados como anexo. **Baixar original** preserva bytes e SHA-256; não se converte um arquivo silenciosamente. Isso é download de arquivos do acervo, não um downloader irrestrito de qualquer site externo.

## PDF como livro funcional

Use **Ler PDF como livro** no cartão do arquivo. PDF.js 6.5.438 (Apache-2.0, compatível com Node 24) renderiza canvas e camada de texto a partir dos bytes originais. Há páginas duplas/simples, virada por botões/setas, zoom, rotação, sumário original quando existente, modo sem animação, texto acessível e última posição no servidor. Não são páginas reconstruídas a partir da extração textual. Imagens/diagramas e a diagramação do PDF permanecem visuais; o download conserva o arquivo original.

Fontes padrão, CMaps e decodificadores são servidos pelo próprio site e suas licenças acompanham o build. JavaScript, anexos e formulários do PDF não são executados pelo leitor. PDFs protegidos podem exigir leitor externo com senha; há acesso ao original. Só as páginas exibidas são renderizadas; as superfícies canvas são limitadas. O leitor precisa de rede para buscar o original e salvar posição; não adiciona PDFs privados ao cache público da PWA.

## MP3/MP4: transcrição sem API paga

O adaptador local usa **OpenAI Whisper tiny multilíngue em CPU**, limitado a 30 minutos por arquivo. Não baixa modelo no upload, não usa a chave Groq e não envia áudio para APIs. O instalador é opcional e explícito:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg tesseract-ocr tesseract-ocr-por
bash scripts/install-transcription.sh
```

Depois, reinicie a SALY e use **Transcrever fala localmente** no cartão de áudio/vídeo. O texto real, com tempos, será indexado. Em vídeo, a transcrição se soma aos quadros OCR. Revise erros: transcrição/OCR não são compreensão completa de cenas, movimentos ou sons não verbais.

O script instala PyTorch pela distribuição CPU e `openai-whisper==20250625`, baixa `tiny.pt` da origem oficial e confere SHA-256 antes de instalar/carregar. Motor e pesos são MIT, conforme README/LICENSE oficiais consultados em 2026-11-16:

- https://github.com/openai/whisper
- https://github.com/openai/whisper/blob/main/LICENSE
- SHA-256 do checkpoint tiny: `65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9`.

**Bloqueio observado aqui:** o download de `openaipublic.azureedge.net` recebeu CONNECT 403 da política de rede. Torch/Whisper/modelo não foram instalados e nenhuma transcrição de fala real foi certificada neste ambiente. A interface mostra indisponibilidade e a API retorna 503; metadados ou uma transcrição fictícia não são usados como substituto. O instalador pode ser executado no Codespaces da proprietária se sua rede permitir. É uma instalação local que utiliza CPU/disco da hospedagem, sem habilitar serviço pago. `SALY_SMOLIN_WHISPER_MODEL_PATH`, opcional, aponta para o checkpoint oficial; vazio usa `.tools/whisper/tiny.pt`.

## Atualizar e verificar

Faça backup privado e pare o servidor atual. Na branch de desenvolvimento:

```bash
cd /workspaces/nexora
git fetch origin
git switch feat/saly-smolin
git pull --ff-only
bash scripts/install.sh
SALY_SECURE_COOKIE=1 bash scripts/start.sh
```

Abra a porta 8000 como privada. `install.sh` recompila o frontend e inclui PDF.js; `start.sh` sozinho não recompila. Não recrie a senha da proprietária nem apague o banco. No ambiente Codex, o checkout é `/workspace/nexora`.

Verificações reproduzíveis:

```bash
.venv/bin/python -m pytest backend/tests/test_smolin_files.py -q
npm --prefix frontend test
npm --prefix frontend run build
.venv/bin/python scripts/browser_smolin_files.py
```

Testes incluem binário/download íntegro, Range, blocos idempotentes/cancelamento/limites, rollback do original e metadados, Office/EPUB/ZIP/textos, XML hostil rejeitado, imagem OCR real, MP4 real com OCR/citação de tempo e MP3 real. Chromium exercita erro HTML controlado, arquivo grande, diagrama colorido original no canvas, seleção de texto, virada, zoom/rotação, posição retomada, checksum intacto, reprodução MP3/MP4 e viewport móvel. A falha HTML é uma reprodução controlada, não diagnóstico definitivo do proxy do seu Codespace. Transcrição real e Android físico continuam não comprovados.
