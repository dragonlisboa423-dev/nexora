# Seletor de modelo e pequeno ajuste visual

A frase “Um espaço para suas ideias crescerem.” foi removida abaixo de “Olá. Eu sou Saly.”. Esfera, shaders, navegação, vozes e dados não foram alterados.

O seletor agora fica sempre visível no chat. Opções de conexão/padrão ficam recolhidas para manter o painel compacto. Mostra Granite 4 3B e Phi-4 Mini, além do provedor remoto e de outros modelos já instalados/selecionados. Não baixa modelos automaticamente.

Configurações → Sistema recebe o ID da conversa aberta e muda essa mesma conversa. **Usar também como padrão** é uma ação separada para as próximas conversas. Trocas preservam histórico e metadados das respostas anteriores. A interface aguarda a confirmação de salvamento e atualização do estado antes de liberar o envio; respostas atrasadas de uma consulta anterior não substituem o estado mais recente. Falhas são exibidas no painel e a seleção é recarregada do servidor.

Selecionar não equivale a instalar ou verificar um modelo. Quando ele está instalado, **Testar modelo local** faz uma geração textual real; somente depois do resultado confirmado o envio é liberado. A interface informa separadamente modelo ausente, Ollama desligado, memória insuficiente e falha de comunicação. Ferramentas e visão locais continuam sem validação; o cartão de conexão local não chama o teste do provedor remoto.

Outra causa possível de a troca não aparecer é uma interface antiga: `git pull` não atualiza `frontend/dist`, que é ignorado pelo Git. `scripts/start.sh` agora verifica a data dos arquivos de entrada e reconstrói o frontend antes de iniciar o backend quando necessário. Build com erro impede servir a interface antiga. Se faltarem dependências, execute `bash scripts/install.sh`.

No Codespace do proprietário, interrompa a SALY com Ctrl+C e execute:

```bash
cd /workspaces/nexora
git pull --ff-only
bash scripts/start-ollama.sh
SALY_SECURE_COOKIE=1 bash scripts/start.sh
```

Atualize a página. Se estiver instalada como PWA e houver o aviso de nova versão, clique em **Atualizar agora**. Não apague dados offline ou credenciais.

Verificações desta alteração: 20 testes Python direcionados (instalador/início e integração existente), 21 testes Vitest, build de produção, Ruff e sintaxe Bash. `scripts/browser_model_selection.py` usa backend real e um servidor de **protocolo Ollama controlado**, em banco descartável: seletor visível, subtítulo ausente, verificação/habilitação, bloqueio durante geração, salvamento recusado sem falsa confirmação, troca em Configurações na mesma conversa, IDs roteados e histórico preservado, recarga/reabertura e celular. Esse teste controlado requer a porta 11434 livre e nunca encerra um Ollama real que esteja rodando. Não é teste com pesos reais, nem comprovação de instalação no Codespace do usuário. `scripts/browser_integrated_update.py` também verifica ZIP, controle do núcleo, transparência do bloom e largura móvel sem erros JavaScript.
