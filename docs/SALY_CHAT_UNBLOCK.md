# Correção do bloqueio de envio com modelos locais

O fluxo anterior exigia `model_ready=true` para habilitar o botão Enviar. Porém, o instalador salvava o teste em `.tools/ollama/probe.json`, enquanto a aplicação consultava `app_config` no banco. Um teste concluído pelo instalador não liberava o chat; interromper o teste após os downloads também deixava os pesos instalados sem caminho direto para testar a primeira mensagem. Num ambiente novo, o modelo padrão ainda era o provedor remoto, mesmo sem chave.

## Comportamento corrigido

- `can_chat` indica que há um modelo instalado no Ollama acessível e que o proprietário pode **tentar** uma geração. Não certifica capacidade ou resposta correta. `model_ready` continua separado e exige geração textual completa vinculada ao digest atual.
- Um modelo instalado permite enviar a primeira mensagem, sem prova prévia ou clique obrigatório em Testar. Somente um stream completo (`done=true`) com texto não vazio registra a verificação. Respostas vazias, erros e streams incompletos não criam respostas concluídas nem verificação positiva. Cancelamento não certifica geração.
- O estado é atualizado imediatamente após terminar/falhar o envio, incluindo o seletor; deixa de depender só do polling de 15 segundos. Falhas de memória/servidor aparecem como erro e permitem uma nova tentativa **manual**, sem repetição automática, resposta simulada ou fallback remoto.
- Perfis novos sem escolha salva e sem provedor remoto configurado usam um dos dois modelos compactos instalados: Granite 4 3B ou Phi-4 Mini. São priorizados os já verificados. Consulta de disponibilidade não gera texto. Configuração remota existente e escolhas explícitas, inclusive por conversa, são preservadas. Escolher local e ficar sem Ollama não envia nada a outro provedor.
- `scripts/probe-ollama.py` e o teste da interface agora usam a mesma rotina, o mesmo banco/configuração da SALY e o mesmo vínculo ao digest. O instalador imprime progresso antes de cada teste, persiste o relatório após cada modelo e retorna erro se algum falhar. Ctrl+C preserva pesos e verificações já concluídas; o primeiro envio pode realizar a validação depois. O teste opcional usa somente uma pergunta fixa, sem enviar memórias/documentos.
- O diagnóstico produzido pelo chat não guarda cópias de mensagens ou respostas: apenas resultado, digest, duração e escopo. O relatório JSON do teste dedicado pode conter a resposta à pergunta fixa; é criado atomicamente com permissão privada. JSON antigo de relatórios não é importado como prova de geração.

Downloads não foram alterados: o instalador mantém apenas Granite/Phi, guardas de disco/RAM e downloads sequenciais. Não houve mudança de senha, chave, plano, memórias, documentos, identidade visual ou shaders. Mantidos contexto 8192, quatro threads, uma geração/modelo carregado por vez e `keep_alive=0`; descarregamento explícito também é solicitado no encerramento/cancelamento. Ferramentas/visão locais continuam sem certificação. Modelo instalado pode falhar por memória, tempo ou formato da resposta: o erro real será mostrado.

## Aplicar no Codespace

Estas mudanças estão no código publicado; este ambiente de desenvolvimento não controla o processo que roda no Codespace do proprietário. Pare a SALY no terminal com Ctrl+C e execute:

```bash
cd /workspaces/nexora
git pull --ff-only
bash scripts/start-ollama.sh
SALY_SECURE_COOKIE=1 bash scripts/start.sh
```

O início reconstrói a interface se houver fontes mais recentes. Atualize a página (ou use Atualizar agora no aviso da PWA). Escolha Granite ou Phi caso uma preferência explícita anterior ainda esteja no provedor remoto e envie uma mensagem. Não é necessário apagar/reinstalar os modelos nem executar o instalador completo para desbloquear o primeiro envio.

O teste opcional, agora compartilhado com a aplicação, continua disponível:

```bash
.venv/bin/python scripts/probe-ollama.py
```

Aguarde os resultados ou interrompa com Ctrl+C. Instalação e validação textual são estados distintos. O site/PWA usa os modelos **do servidor**, não instala inferência no Android e depende do Codespace/rede disponíveis.

## Verificações realizadas

- Backend completo: **186 testes passaram**, 1 teste PostgreSQL ignorado por ausência de serviço. Incluídos envio sem probe, perfil novo local, respeito a escolha remota/configuração existente, digest alterado, resposta vazia/truncada, memória insuficiente sem repetição e cancelamento sem falsa verificação. Sem resposta privada duplicada no registro de prontidão.
- Frontend: **21 testes Vitest**, build de produção, Ruff e diff verificados. Permanece o aviso de tamanho dos bundles Three/PDF.
- Chromium (`scripts/browser_model_selection.py`): interface e backend reais com **protocolo Ollama controlado**, banco temporário e relatório separado. Primeiro envio sem teste prévio, metadados corretos por modelo, CLI gravando prontidão que a aplicação lê imediatamente, troca na mesma conversa, histórico/reabertura, falha ao salvar sem falsa confirmação, desktop/celular e ausência de erros JavaScript.
- Chromium (`scripts/browser_integrated_update.py`): seletor persistente, ZIP/bytes privados, controle do núcleo, transparência do bloom e largura móvel.
- Runtime nativo Ollama 0.40.16: servidor acessível, catálogo vazio neste workspace. O novo CLI retornou erro de modelo ausente, sem certificar funcionalidade. `registry.ollama.ai` continua bloqueado por CONNECT HTTP 403 na rede deste ambiente; os testes controlados **não são inferência com os pesos reais** nem prova de resposta no Codespace do proprietário. A imagem enviada pelo proprietário confirma downloads terminados lá, mas não comprova a geração.
