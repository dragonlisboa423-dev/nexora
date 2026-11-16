# Vozes · capacidades e evidências

## Provedores atuais

| Provedor | Estado | Limites |
|---|---|---|
| Web Speech API | Existente, dependente do navegador/dispositivo | Lista somente vozes detectadas; pode enviar áudio a serviço do navegador. Não entrega PCM para análise da saída. |
| eSpeak NG | Adaptador independente implementado e testado neste ambiente | CPU no servidor, sem API paga. pt-BR com variante `f3` marcada feminina no arquivo do motor. Síntese por formantes, artificial; não é voz neural, exclusiva ou equivalente à naturalidade solicitada. |
| Kokoro `pf_dora` | Não instalado/não configurado | Consulta ao model card oficial bloqueada com CONNECT 403. Pesos/licença do artefato e compatibilidade não foram certificados aqui. |
| Piper | Não instalado/não configurado | Motor/modelo ainda não selecionados com análise de licenças. Não se distribuiu pacote de vozes. |

`backend/voices.py` implementa `SpeechProvider` e `VoiceCatalogProvider`. `GET /api/voices` informa a configuração e candidatos indisponíveis, sem marcar uma voz como comprovada só por existir código. `POST /api/voices/preview` e `/synthesize` exigem autenticação, limitam texto a 3000 caracteres, controlam taxa, serializam processos e validam WAV/PCM antes de responder. Não guardam texto ou áudio por padrão e não enviam conteúdo a terceiros. Um timeout ou falta de dependência produz falha explícita.

O catálogo usa `saly-espeak:pt-br-f3` como URI de seleção. A preferência/perfil persiste nas configurações existentes. A prévia pode ser ouvida antes da seleção e baixada como WAV. Velocidade/tom são controles básicos do motor, sem alegação de prosódia emocional avançada. Voz exclusiva, clonagem, timestamps por palavra e naturalidade neural não estão implementados.

## Instalação/configuração

Nenhuma voz é baixada automaticamente no frontend. Em um servidor Debian/Ubuntu administrado pela proprietária, instale o pacote oficial compatível `espeak-ng` pelo gerenciador do próprio sistema e preserve seus avisos de licença. Se o binário estiver no PATH, o adaptador o detecta. A instalação exige a autorização/permissão do administrador desse servidor; a SALY não executa sudo por chat.

Opcionalmente configure no ambiente privado:

```dotenv
SALY_ESPEAK_BINARY=/caminho/revisado/espeak-ng
SALY_ESPEAK_DATA_PATH=/caminho/revisado/espeak-ng-data
SALY_ESPEAK_LIBRARY_PATH=/caminho/revisado/bibliotecas
```

Deixe os caminhos de dados/bibliotecas vazios na instalação normal do sistema. Não copie os caminhos específicos deste executor como se já existissem no Codespaces. Sem binário/dados compatíveis, o catálogo informa não configurado; não há troca silenciosa para outra voz quando a voz local selecionada falha.

Neste executor Debian 13, o helper de instalação de sistema estava indisponível. Foram extraídos pacotes oficiais Debian em `.tools/espeak`, pertencente ao usuário, sem executar scripts de manutenção. Versões verificadas no índice oficial: `espeak-ng`, `espeak-ng-data` e `libespeak-ng1` `1.52.0+dfsg-5`; `libpcaudio0` `1.3-1`; `libsonic0` `0.2.0-13+b1`. Tamanho e SHA-256 foram comparados com o índice HTTPS Debian antes da execução. Os avisos `copyright` do motor/dados foram lidos: GPL-3.0-or-later com exceções/avisos de componentes. A extração não foi commitada nem virou instalação automática universal. Redistribuição de binários exige preservar as licenças e cumprir as obrigações de código-fonte correspondentes.

## Áudio e núcleo

O frontend obtém WAV autenticado, decodifica em `AudioContext`, reproduz e mede o sinal real com `AnalyserNode`. Pausar suspende o contexto e zera o medidor; parar cancela requisição/reprodução e encerra o contexto. O núcleo usa a amplitude medida para energia/ondas; não usa oscilação senoidal para simular waveform. Em Web Speech, mostra apenas estado/eventos reais, sem alegar amplitude que a API não fornece. O estilo orgânico foi preservado.

eSpeak pode sintetizar sem internet no servidor onde está instalado. Isso **não** permite ao celular alcançar um backend remoto em modo avião. Voz própria no aparelho e inferência local são capacidades distintas, ainda não instaladas. Reconhecimento continua sendo o do navegador, com microfone explícito e aviso sobre processamento externo; não há escuta oculta nem garantia com navegador fechado.

## Validação

Dois testes de API passaram com síntese real: WAV mono 22050 Hz, PCM não vazio/variável, frases diferentes, proteção de conteúdo e falhas de configuração/autorização. Chromium baixou um WAV real, verificou playback/pausa/retomada/parada e persistência da seleção. Em um chat de transporte textual controlado, o botão Ouvir sintetizou pelo motor real e a amplitude PCM comandou o núcleo; pausa/parada retiraram as ondas. Nenhum LLM foi chamado. A saída foi validada digitalmente; não se certificou alto-falante físico nem naturalidade perceptual.

Comandos:

```bash
.venv/bin/python -m pytest backend/tests/test_voices.py -q
.venv/bin/python scripts/browser_voice.py
```

Se o motor real estiver ausente, o teste de síntese é explicitamente pulado e o script de navegador recusa declarar sucesso. Instalação no Codespaces/telefone e uma voz neural natural continuam pendentes.
