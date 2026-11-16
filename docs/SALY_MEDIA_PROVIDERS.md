# Estúdio Multimídia — capacidades comprovadas

## Implementado e exercitado

- Upload privado de PNG/JPEG/WebP estáticos, clipes MP4/WebM e áudio decodificável, com limite de entrada de 10 MB/60 s. Imagens têm limite adicional de 8 MB/16 MP. Imagens são normalizadas; AV é decodificado/reexportado por FFmpeg para MP4 H.264/AAC ou WAV mono 22050 Hz. Não há URL remota, playlist, OCR ou transcrição automática.
- Recorte e rotação reais com Pillow, preservando a imagem de origem. É edição local, não edição generativa.
- Montagem FFmpeg real de até oito cenas/60 s, duração e corte por cena, preservação de proporção, texto fixo de legenda, corte ou fade para preto, narração/música e exportação 640×360 ou 360×640. Áudio original dos clipes é removido. Duas faixas usam mistura com música a 20%; faixas curtas repetem. Não são cenas geradas por IA.
- Histórico persistente com `queued`, `running`, `cancel_requested`, `cancelled`, `completed`, `failed`. Progresso usa `out_time_us` do FFmpeg sobre duração da etapa, não tempo inventado. Cancelar interrompe processo local e remove temporários. Reinício não repete uma inferência remota interrompida.
- Resultado só é concluído após validação, hash e armazenamento privado. Binários são BLOBs com MIME/SHA-256; downloads e exclusões exigem sessão. Arquivos permanecem até exclusão explícita. Temporários de cada execução são removidos ao encerrar/cancelar. Exclusão do histórico remove suas saídas, preservando entradas.

Motor observado: FFmpeg/FFprobe 7.1.5, build GPLv2-or-later, fonte DejaVu Sans local para legendas. No Codespaces, verifique `ffmpeg -version`/`ffprobe -version`; se ausentes, instale pelos pacotes oficiais do seu sistema, por exemplo `sudo apt-get update` seguido de `sudo apt-get install -y ffmpeg fonts-dejavu-core`. São dependências nativas gratuitas; licenças e disponibilidade da distribuição se aplicam. A imagem Docker anterior não inclui esses pacotes automaticamente. Não foi certificado um build Docker nesta rodada.

## Imagens por IA — conector implementado, geração externa bloqueada

`ImageGenerationProvider` possui adaptador Cloudflare Workers AI para **FLUX.1 schnell**. O contrato oficial consultado aceita `prompt` de 1–2048 caracteres e `steps` até 8, retornando Base64 em JSON; não inventamos parâmetros de largura/altura. O backend limita resposta, decodifica, valida e normaliza o arquivo. Sem fallback pago ou repetição automática. Há limite local conservador de **uma tentativa por dia UTC**, reservada antes de enviar, mesmo em caso de falha. A franquia da conta é compartilhada e esse limite não mede Neurons restantes.

Documentação oficial foi obtida em 2026-11-16 pelo repositório público `cloudflare/cloudflare-docs`, após o domínio developers.cloudflare.com receber bloqueio de rede. Snapshots estão em `docs/providers/`; não são instruções executáveis. Originais:

- https://github.com/cloudflare/cloudflare-docs/blob/production/src/content/workers-ai-models/flux-1-schnell.json
- https://github.com/cloudflare/cloudflare-docs/blob/production/src/content/workers-ai-models/flux-2-klein-4b.json
- https://github.com/cloudflare/cloudflare-docs/blob/production/src/content/docs/workers-ai/platform/pricing.mdx

A documentação informa **10.000 Neurons/dia**, reset às 00:00 UTC. Workers Free bloqueia excedente; Workers Paid pode cobrar. Não pressupomos imagens ilimitadas nem que a presença do modelo assegure gratuidade/termos da conta. Metadados apontam termos BFL em https://bfl.ai/legal/terms-of-service; revisão desses termos e condições aplicáveis aos artefatos/uso da conta continua pendente. Não tratamos licença do código de um modelo como licença automática de seu serviço ou pesos.

Para habilitar posteriormente, a proprietária precisa confirmar **Workers Free, sem faturamento ou gateway pago**, revisar os termos vigentes e configurar exclusivamente no servidor `SALY_CF_ACCOUNT_ID`, `SALY_CF_API_TOKEN`, `SALY_CF_WORKERS_FREE_CONFIRMED=1` e `SALY_CF_TERMS_REVIEWED=1`. Esses indicadores são declarações administrativas; o software não certifica a contratação da conta. Deixe ambos em 0 até concluir a revisão. Não envie tokens no chat. Nenhum valor foi preenchido ou alterado neste trabalho. A primeira geração real deve ser solicitada manualmente no Estúdio, conferindo arquivo/checksum e quota no painel.

Não há conta/credencial Cloudflare disponível neste ambiente e o acesso de inferência não foi testado. O teste do adaptador usa transporte controlado e **não comprova geração real**. Cancelamento de imagem é local: o provedor pode consumir cota após o envio. Edição generativa FLUX.2 Klein depende de validar parâmetros multipart detalhados, termos e execução real; não está habilitada.

## Vídeos por IA — não configurado

`VideoGenerationProvider` tem implementação explícita de indisponibilidade. Nenhum modelo/GPU/provedor gratuito foi conectado. A API retorna 503 e a interface não fabrica vídeos para apresentar sucesso. Nenhuma API paga, cartão ou crédito foi ativado.

## Verificação

Oito testes Python de mídia passaram, incluindo MP4 real, legendas/transições, clipe reexportado, duas faixas, cancelamento com FFmpeg em execução, arquivo/histórico/exclusão e contrato Cloudflare com transporte controlado. `browser_studio.py` passou com upload, rotação, exportação, download/checksum, reprodução nativa com `currentTime > 0`, recarga de histórico e viewport móvel. O teste encontrou largura excessiva no móvel, corrigida e verificada. Não comprova inferência externa, reprodução física no Android ou certificação de licenças dos arquivos enviados.
