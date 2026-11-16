# SALY Intelligence · entrega incremental de 2026-11-16

A aplicação existente foi evoluída em commits por fase. Núcleo cinematográfico, fallback 2D, identidade visual, conversas, memória, Smolin, autenticação e configuração Groq foram preservados. Nenhuma credencial foi inventada ou alterada; nenhuma API paga foi habilitada. Esta entrega não significa que dependências externas pendentes se tornaram funcionais.

## Matriz atual

| Área | Demonstrado | Limite atual |
|---|---|---|
| Core e JSON | Prévia/erros úteis, revisão administrativa da semente, backup, regras no fluxo, ferramentas determinísticas e rastros por resposta | ZIP modular/SALY_Core_v1 ausentes; não treina pesos nem certifica raciocínio geral/AGI. |
| Memória | Persistência SQL, versões, exclusão de derivados e cofre opt-in com conflito/idempotência | Encoder semântico real não conectado aqui; não é memória cognitiva humana. |
| Voz | eSpeak pt-BR variante feminina, WAV/PCM real, pausa/retomada/parada e amplitude do núcleo | Formantes artificiais. Voz neural natural/exclusiva e dispositivo físico pendentes. |
| Agenda/alarmes | Eventos, recorrência, conflitos, scheduler persistente, adiamento e histórico; consulta offline selecionada | Backend e interface ativos para avisos; sem Push/alarme nativo/exatidão garantida. Eventos/novos alarmes não são editados offline. |
| Compras | Manual, centavos, orçamento/categorias/parcelas, comprovantes privados e alertas opcionais | Sem OCR/rastreamento/pagamentos. Comprovantes não são copiados offline; orçamento local é consulta. |
| Espaço | Gavetas, posição/cor/ícone, links/etiquetas/favoritos/movimento, importação/exportação atômica, fila offline | Páginas externas precisam de rede; URL válida não certifica reputação. |
| Biblioteca | Autoria manual, versões, revisão/publicação imutável, leitor duplo/único/vertical, fontes, mídia privada, progresso/notas | Autoria continua online; nenhum acervo protegido foi importado. |
| Biologia | Nove páginas originais em rascunho, oito capítulos estruturados, quizzes, célula, DNA, logística e microscópio esquemático | Revisão editorial/científica pendente; capítulos futuros sem conteúdo, sem micrografia/calibração física/3D anatômico. |
| Livros offline | Cópia seletiva criptografada, mídias escolhidas com hash, leitura/atividades, progresso/notas, conflitos e exclusão remota | Mídia até 5 MB cada; cofre total 30 MB; tutoria remota/narração de servidor exigem rede. |
| Agente nos novos módulos | Consultas reais tipadas a compras/orçamento/links/livros, desativadas até consentimento específico | Sem pagamento, publicação automática ou acesso a comprovantes. Conexão atual Groq não foi revalidada sem a chave do servidor da proprietária. |
| Imagens | Upload, galeria, recorte e rotação locais reais; adaptador FLUX.1 com guardas | Geração externa não testada: faltam conta/token/termos; edição generativa FLUX.2 bloqueada. |
| Vídeos | Montagem FFmpeg com cenas, cortes, legendas, fades, duas trilhas, progresso/cancelamento, MP4 validado/baixado/reproduzido | Não é geração de novas cenas por IA. Gerador de vídeo por IA não configurado. |
| Laboratório | Core + oito probes de motores/domínios + testes reais de PCM/IndexedDB/cache no navegador, relatórios persistentes | Não testa automaticamente provedores remotos, entrega física, revisão científica ou todo hardware. |
| Android/PWA | Manifesto/ícones, HTTPS/cookie seguro, cache público, layout móvel e cofre offline verificados em Chromium | Instalação em Android físico e APK não executados. Capacitor é viável com adaptação de origem/API/cookies, SDK e testes próprios. |
| Smolin | Originais privados, processamento isolado, busca lexical, citações e exclusão preservados | OCR e qualidade de recuperação semântica com encoder real pendentes. |

## Atualizar no Codespaces existente

Pare o processo antigo com Ctrl+C. Faça um backup privado do banco antes de atualizar. Para SQLite, com a venv existente e a configuração atual:

```bash
cd /workspaces/nexora
mkdir -p /workspaces/saly-backups
.venv/bin/python -m backend.manage backup /workspaces/saly-backups/saly-2026-11-16.sqlite3
git fetch origin
git switch feat/saly-smolin
git pull --ff-only
bash scripts/install.sh
SALY_SECURE_COOKIE=1 bash scripts/start.sh
```

O destino de backup deve ser novo; se já existir, escolha outro nome. PostgreSQL exige backup pelo serviço/pg_dump, não esse comando SQLite. O instalador recompila a interface; `start.sh` sozinho não recompila. As migrações são aditivas. Não apague `.env`, banco, volumes ou `.venv.previous.*` para atualizar. Reutilize a senha da proprietária; não execute `owner` novamente sem querer alterá-la.

Para motores nativos ausentes no Codespaces Debian, instale pelos pacotes oficiais: `sudo apt-get update`, depois `sudo apt-get install -y ffmpeg fonts-dejavu-core espeak-ng`. Isso não instala modelo neural nem habilita serviço pago. No ambiente Codex atual, FFmpeg foi exercitado e eSpeak foi verificado em área do usuário; esses arquivos locais não são distribuídos no Git. Docker/Android físico não foram reconstruídos nesta rodada.

Abra a porta **8000** como **Privada** e use **Abrir no navegador**. Use o link atual da aba Portas, que inclui o nome do Codespace e `-8000.app.github.dev`. A atividade do Codespace do seu navegador não foi verificada a partir deste ambiente separado.

No app: Agenda/Alarmes; Compras; Espaço; Biblioteca; Estúdio Multimídia; Laboratório SALY. Em Privacidade, autorize separadamente consultas pessoais do agente e cópias do Cofre local. O arquivo `SALY_CORE_MEMORY_v1.json` deve usar a revisão administrativa do Core, não o importador de memórias comuns.

## Bloqueios que exigem dados/serviços reais

1. Cloudflare: conta Workers Free sem cobrança, token no servidor e revisão de termos; só então um teste manual real poderá comprovar geração. Não envie token pelo chat. Não confunda o teste de transporte controlado com uma imagem gerada pelo serviço.
2. Vídeo generativo: modelo/provedor/GPU e quota gratuita realmente utilizáveis não disponíveis.
3. Voz natural: artefato neural, licença, download permitido e execução no destino ainda pendentes. eSpeak não satisfaz naturalidade neural.
4. Android físico/APK, Web Push e alarmes nativos: precisam de ambiente/dispositivo/configuração próprios. Não se assume operação com app fechado.
5. Encoder semântico/OCR, revisão científica da edição e pacote Core modular ausente permanecem explicitamente pendentes.

Veja [relatório de testes](SALY_TEST_REPORT.md), [mídia/provedores](SALY_MEDIA_PROVIDERS.md), [orçamento](SALY_FREE_TIER_LIMITS.md) e [instalação Android/offline](INSTALAR_SALY_ANDROID.md).

Verificação desta entrega: **137 Python passaram, 1 PostgreSQL pulado, 12 Vitest e build**, Ruff/formatação/diff sem erros; nove scripts Chromium executados com sucesso nos fluxos documentados, sem inferência externa.
