# Biblioteca interativa e autoria manual

A Biblioteca guarda livros como capítulos/páginas/blocos estruturados validados no backend. O editor cria livros, capítulos e páginas, edita Markdown, fontes, autoria/licença, capa e imagens privadas, reordena páginas/blocos e salva versões. Texto não executa HTML/JavaScript e imagens externas em Markdown são bloqueadas. Blocos são tipos permitidos com configurações limitadas; não há execução de código editorial.

Estados `draft` e `review` são editáveis. Publicar exige última versão salva em revisão e confirmação separada, criando snapshot imutável `published`. Editar ou restaurar versão sempre atua no rascunho e preserva o snapshot publicado. Exclusão de livro remove versões, BLOBs, progresso e anotações. Exportação estruturada não contém binários: recuperação completa exige backup do banco. Mídias referenciadas em versões não podem ser removidas isoladamente, preservando histórico.

Leitor mostra páginas duplas acima de 1000 px e página única abaixo disso, sumário, busca textual, virada por controles/teclado com animação CSS, numeração e sombras. Interações dentro das páginas não ativam virada por gesto. Há modo vertical sem animação e respeito a redução de movimento. Não foi necessária instalação de wrapper React de terceiros. O leitor não impõe altura fixa que oculte conteúdo.

Conclusão de páginas, marcadores, tentativas de quiz e última página ficam no servidor, com revisão para impedir sobrescrita entre abas. Anotações privadas têm criação e exclusão explícitas. Narração usa voz selecionada, com pausa/retomada/parada e limite declarado de 5.000 caracteres por acionamento. Narrar ao mudar página é opcional; não há avanço automático. Voz neural natural permanece pendente conforme `SALY_VOICE_PROVIDERS.md`.

Tutoria prepara livro/capítulo/página/trecho/fontes no campo de conversa mediante confirmação. O texto é dado não confiável para comandos; publicação não é uma ferramenta do modelo. A proprietária revisa e envia, com o consentimento remoto existente. Preparar o campo não chama Groq. A conexão atual não foi testada com credenciais aqui.

Imagens de capa/páginas usam upload privado normalizado. Os contratos permitem áudio/vídeo privados; seu upload depende da etapa multimídia e não é anunciado como disponível antes dela. Microscópio, célula, DNA e ecologia recebem motores didáticos na fase de Biologia. Modelos 3D não são necessários ao fallback 2D; não há modelo anatômico 3D instalado. A cópia de livros no cofre é uma extensão separada; a primeira versão do leitor depende de rede.

Verificação: três testes Python de domínio e `scripts/browser_library.py` com Chromium real passaram, cobrindo autoria, páginas duplas/únicas, progresso, notas, última página, publicação e contexto sem envio. Não comprova revisão científica da proprietária ou Android físico.
