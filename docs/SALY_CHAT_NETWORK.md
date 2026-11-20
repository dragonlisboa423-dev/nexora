# Correção da conexão durante a espera por resposta

O proprietário relatou “Network Error” depois de esperar, tanto com Granite como com Phi. A inspeção encontrou uma lacuna no transporte: depois dos eventos iniciais de contexto, o backend não enviava dados enquanto o modelo carregava/preparava os primeiros tokens. Isso deixa conexões encaminhadas expostas ao corte por inatividade. Não foi possível inspecionar o processo do Codespace do proprietário; a causa exata do episódio relatado não está comprovada.

## Mudanças

- `backend/streaming.py` mantém o NDJSON ativo com um evento `heartbeat` a cada 10 segundos durante os intervalos sem resposta. Esse evento não é token, resposta, prova de geração nem estado operacional inventado; o frontend o ignora.
- Um único produtor mantém os context managers do gerador na mesma tarefa. A fila tem capacidade de um evento para limitar buffering. Desconexão/cancelamento cancela também o produtor e executa a limpeza com espera limitada; não deve deixar uma geração órfã no backend.
- A resposta usa `Cache-Control: no-store, no-transform` e mantém `X-Accel-Buffering: no`. Erros inesperados após o início dos headers viram evento de erro sanitizado com código de referência, em vez de encerrar abruptamente o stream. O log contém código/tipo, sem o conteúdo privado da exceção.
- Timeout de leitura do Ollama, prazo total da resposta e falha de transporte agora têm explicações distintas. Um corte real do navegador orienta conferir o Codespace/SALY e reabrir a conversa antes de reenviar: uma conexão perdida não permite afirmar se uma resposta completa foi salva ou não.
- Resposta HTTP de proxy em HTML é tratada pelo status HTTP; não vira erro de parsing JSON. Respostas inválidas/incompletas e sessão privada recusada também recebem mensagem adequada.
- Não há reenvio automático de perguntas, fallback pago ou resposta de substituição. Não foram alterados os pesos, credenciais, dados, interface do núcleo, limite de RAM ou parâmetros de inferência. O modelo continua com contexto 8192, saída máxima 1400 tokens, uma geração por vez e descarregamento ao encerrar. Os limites de espera continuam 180 s de leitura do runtime local e 240 s de operação total do chat; manter o transporte vivo não garante que o modelo conseguirá responder dentro deles.

## Verificação

- **191 testes Python aprovados**, 1 PostgreSQL ignorado por falta de serviço: inclui espera assíncrona com heartbeats, preservação do contexto da tarefa, cancelamento com limpeza, erro sanitizado após headers, timeout do modelo e prazo total sem resposta parcial salva.
- **25 testes Vitest aprovados**, build de produção e Ruff/diff verificados. Continua o aviso conhecido de tamanho dos bundles Three/PDF.
- `scripts/browser_chat_network.py`: Chromium, backend real, banco descartável, protocolo de modelo **controlado** e proxy real com limite de inatividade de 0,35 s. A resposta atrasada 1,2 s atravessou o proxy com 12 heartbeats (intervalo de teste 0,1 s). Uma desconexão forçada em seguida mostrou o erro esperado no navegador, não reenviou a pergunta e não criou uma segunda resposta concluída; sem erros JavaScript não tratados.
- `scripts/browser_model_selection.py`: passou a integração existente de primeiro envio, validação do instalador no banco da aplicação, troca de modelo, histórico, desktop e celular.
- O teste de proxy requer a porta 11434 livre para o servidor controlado e nunca encerra um Ollama real existente. Não comprova desempenho com os pesos reais. O acesso ao registro do Ollama neste workspace continua bloqueado por CONNECT HTTP 403, e este workspace não é o Codespace do proprietário.

## Aplicar no Codespace

Pare a SALY com Ctrl+C no terminal que executa o servidor e use:

```bash
cd /workspaces/nexora
git pull --ff-only
bash scripts/start-ollama.sh
SALY_SECURE_COOKIE=1 bash scripts/start.sh
```

A interface é reconstruída pelo início quando as fontes são mais recentes. Atualize a página ou aplique a atualização da PWA. Não é necessário reinstalar ou baixar os modelos outra vez para aplicar esta correção.

Se ainda houver falha, o novo texto/código ajuda a distinguir transporte, tempo e servidor. No Codespace, consulte a RAM e o log do runtime, sem exibir `.env` ou chaves:

```bash
free -h
tail -n 30 .tools/ollama/server.log
```

Código de rede não consegue recuperar uma conexão se o Codespace for suspenso, o backend for encerrado ou faltar memória ao sistema. Nesses casos é necessário verificar o processo e o diagnóstico do ambiente real.
