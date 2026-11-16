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

IA Groq, reconhecimento remoto e novas consultas externas não funcionam sem internet. Configurações, orçamento e agenda/alarmes são snapshots de consulta. Escrita offline inclui memórias, tarefas, compras e gavetas/links com consentimento. Livros baixados permitem leitura, atividades, progresso e novas notas; autoria de livros continua online. Originais de documentos e mídias são escolhidos individualmente. Após sair de uma sessão expirada, volte ao espaço online para autenticar antes de sincronizar.

Capacitor continua viável para reaproveitar `frontend/dist`, sem duplicar a interface; requer configuração de origem/API/cookies, armazenamento e permissões nativas, Android SDK/JDK e teste de alarmes. Não foi instalado nesta fase. PWA/Push não equivalem a alarme exato com navegador fechado e não instalam um modelo de IA local.

## Novas áreas e modo avião

No Cofre local, **Compras e Espaço locais** pede autorização adicional para dados financeiros/links. Crie um registro, desligue a rede, recarregue e sincronize depois. Comprovantes continuam apenas no servidor. Em **Agenda e alarmes guardados**, autorize uma fotografia para consulta: ela não dispara alarmes offline. Em **Livros guardados**, consulte catálogo, escolha rascunho/publicada e autorize o livro. Incluir mídias exige marcação separada (5 MB cada; cofre total 30 MB). Atividades de Biologia executam cálculos locais; tutoria/modelo remoto e voz de servidor não funcionam sem rede.

No teste em modo avião, confirme a imagem escolhida, avance página, conclua leitura e guarde uma nota. Ao reconectar, progresso e notas sincronizam; divergência de progresso exige escolha. Notas usam IDs idempotentes para não duplicar ao repetir. Uma cópia limpa de livro excluído no servidor é removida na próxima sincronização; se houver rascunho pendente, fica conflito para exportar/decidir, sem recriar o livro. Remova cópias apenas depois de exportar o que deseja manter.

## Viabilidade de Capacitor

Reaproveitar React/Vite é viável, sem duplicar a interface. Porém o bundle usa `fetch('/api')` e sessão HttpOnly no mesmo domínio: em um WebView empacotado, `/api` apontaria para a origem local. É necessário definir uma estratégia de backend HTTPS/origem e cookies, rever CORS/CSRF com allowlist exata e validar autenticação no WebView. Não se deve abrir `*` ou expor chave Vite para contornar isso. Um wrapper que apenas carrega o site remoto não oferece offline nativo automaticamente.

Há Java 21 neste ambiente, mas Android SDK/adb e projeto Capacitor não foram encontrados. Nenhum APK/AAB foi gerado, assinado ou testado. Para alarmes exatos seriam necessários plugins/permissões/restrições Android específicos, além de testes com economia de bateria e processo encerrado. Cofre Chrome e armazenamento do WebView têm origens distintas e exigem migração explícita por backup, sem presumir compartilhamento de senha/chave. Prioridade atual: PWA HTTPS; APK requer etapa própria de implementação/validação.
