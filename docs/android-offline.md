# HTTPS, Android e modo avião

## Publicação HTTPS

O repositório não hospeda sozinho o backend ou o banco. Use uma instalação existente ou a opção de `deployment.md`, com volume persistente, chave somente no servidor, autenticação da proprietária, HTTPS e `SALY_SECURE_COOKIE=1`. Nenhum serviço foi contratado ou publicado nesta etapa. Confirme quota e condições de qualquer plano antes de criar recursos; o orçamento inicial é R$ 0.

No Codespaces, mantenha a porta 8000 privada e abra pelo encaminhamento HTTPS. O ambiente precisa estar em execução. Não use `localhost` do computador/telefone como se fosse o servidor remoto. Evite mudar de origem se quiser manter a instalação PWA e o cache no mesmo domínio.

## Instalar a PWA no Chrome Android

1. Inicie o servidor e abra no Chrome do telefone a URL HTTPS encaminhada da aplicação, incluindo `-8000.app.github.dev` no caso do Codespaces. Use **Portas → Abrir no navegador** para obter a URL atual, em vez de copiar o endereço do editor.
2. Autentique-se no GitHub, se o encaminhamento privado exigir, e desbloqueie a SALY com sua senha privada.
3. Aguarde carregar a página com internet. No menu do Chrome, escolha **Instalar aplicativo** ou **Adicionar à tela inicial**; o nome pode variar. O botão de instalação da SALY aparece quando o navegador emite o evento correspondente.
4. Abra pelo ícone SALY e confira tela inicial, navegação, tamanho do texto e envio de mensagens com o servidor online. A PWA usa a mesma interface do site, manifesto e ícones próprios existentes.
5. Se não houver opção de instalação, verifique HTTPS, manifesto/service worker no DevTools remoto, instalação anterior e as restrições do navegador/perfil. Não confunda atalho instalado com backend hospedado ou modelo local.

Esses passos são instruções para o dispositivo da proprietária. Esta entrega testou viewport móvel em Chromium, não uma instalação física Android.

## Teste honesto em modo avião

1. Com internet, abra a SALY, espere o service worker ativar e recarregue uma vez.
2. Confira que os dados necessários continuam no servidor; não presuma que visualizar uma memória a copiou para o telefone.
3. Ative modo avião e desligue também Wi-Fi, caso permaneça ligado. Abra/recarregue a PWA.
4. **Resultado esperado nesta versão:** página pública de indisponibilidade com aviso de falta de conexão. O cache contém somente recursos públicos do frontend; não APIs, documentos, memórias, senha ou chave.
5. **Ainda não esperado:** documentos/memórias/configurações privadas editáveis offline e conversa com IA. Não há IndexedDB de conteúdo privado nem motor/modelo local funcional integrado nesta versão.
6. Reative a rede, confirme que o servidor está ativo e recarregue. Confira login, documentos e memórias persistidos no servidor. Registre dispositivo, Chrome, origem, timestamp e falhas no relatório do teste.

O teste automatizado existente verifica cache público, ausência de rotas `/api` no Cache Storage e fallback sem rede. Ele não prova funcionamento em qualquer Android, persistência contra limpeza do navegador ou inferência local. A permissão `navigator.storage.persist()` e cópias locais gerenciáveis ainda precisam ser implementadas; o navegador pode remover armazenamento sob pressão.

## Viabilidade de APK com Capacitor

É viável reaproveitar o React/Vite existente e seu `dist`, sem duplicar a interface. Ainda não há projeto Capacitor nem APK gerado, assinado ou testado. A avaliação desta etapa é arquitetural; Capacitor/Android SDK não foram instalados.

Antes de produzir o APK, é preciso configurar origem/API HTTPS e cookies/autenticação para o WebView (hoje as rotas `/api` são relativas à mesma origem), restringir navegação, avaliar permissões de microfone/arquivos e implementar armazenamento local seguro. Não resolver isso desativando validação de origem, tornando o banco público ou embutindo chaves de provedor no APK. A versão PWA continua usando o mesmo frontend; adaptações nativas devem ficar em módulos de plataforma.

O build requer Android SDK/JDK/Gradle e teste em aparelho/emulador. APK local não exige por si só contratar uma API; distribuição em loja pode ter taxas e não foi autorizada. Capacitor não fornece IA offline: isso exige separadamente motor compatível, pesos licenciados, limites de RAM/armazenamento, tempo de carregamento, consumo térmico e execução real no aparelho. Nenhuma dessas dependências está comprovada aqui.
