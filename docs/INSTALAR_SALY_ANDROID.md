# SALY no Chrome Android e teste offline

Não foi gerado APK nem executado teste físico Android. A interface é a mesma React/Vite do site. Há evidência de Chromium desktop com viewport móvel; permissões e persistência precisam ser verificadas no aparelho real.

1. Atualize, compile o frontend e inicie a mesma aplicação com HTTPS, sessão privada e `SALY_SECURE_COOKIE=1`. No Codespaces, mantenha a porta 8000 privada e abra a URL encaminhada da aplicação, não a do editor.
2. No Chrome Android, desbloqueie a SALY. Aguarde o service worker e recarregue uma vez. Use o menu **Instalar aplicativo / Adicionar à tela inicial**, quando oferecido.
3. Em **Configurações → Privacidade**, abra **Cofre local**. Com sessão online válida, escolha senha local de pelo menos oito caracteres e autorize explicitamente a cópia de memórias, lembretes e configurações. Não use a chave Groq como senha.
4. Em **Documentos guardados**, escolha individualmente os documentos que deseja baixar. A cópia verifica o checksum e guarda original/texto criptografados; guardar apenas metadados não basta para ler um original offline.
5. Exporte um backup criptografado. A permissão de armazenamento persistente do navegador pode ser recusada e não substitui backup.
6. Ative modo avião e desligue Wi-Fi. Reabra `/offline` pelo app ou pelo link no acesso inicial. Digite a senha do cofre. Confira memórias, agenda local, documento escolhido e configurações copiadas. Crie/edite um rascunho e recarregue para verificar persistência.
7. Reative a rede com o servidor ativo e sessão válida. O cofre sincroniza ao abrir/restabelecer conexão; há também **Sincronizar agora**. Revise conflitos antes de escolher qual versão manter. Exclusões remotas são propagadas; um rascunho concorrente não é reinserido automaticamente.
8. Para restaurar backup, bloqueie o cofre, selecione o arquivo e valide sua senha. O cofre anterior pode ser exportado. A fila restaurada fica pausada até revisão/autorização explícita.

IA Groq, reconhecimento remoto e novas consultas externas não funcionam sem internet. Nesta fase, configuração offline é snapshot de consulta; escrita offline é de memórias e lembretes, e originais são leitura seletiva. As futuras abas não foram automaticamente implementadas por esse cofre. Após sair de uma sessão expirada, volte ao espaço online para autenticar antes de sincronizar.

Capacitor continua viável para reaproveitar `frontend/dist`, sem duplicar a interface; requer configuração de origem/API/cookies, armazenamento e permissões nativas, Android SDK/JDK e teste de alarmes. Não foi instalado nesta fase. PWA/Push não equivalem a alarme exato com navegador fechado e não instalam um modelo de IA local.
