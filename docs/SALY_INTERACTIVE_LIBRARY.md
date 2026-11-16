# Biblioteca interativa e autoria manual

A Biblioteca guarda livros como capítulos/páginas/blocos estruturados validados no backend. O editor cria livros, capítulos e páginas, edita Markdown, fontes, autoria/licença, capa e imagens privadas, reordena páginas/blocos e salva versões. Texto não executa HTML/JavaScript e imagens externas em Markdown são bloqueadas. Blocos são tipos permitidos com configurações limitadas; não há execução de código editorial.

Estados `draft` e `review` são editáveis. Publicar exige última versão salva em revisão e confirmação separada, criando snapshot imutável `published`. Editar ou restaurar versão sempre atua no rascunho e preserva o snapshot publicado. Exclusão de livro remove versões, BLOBs, progresso e anotações. Exportação estruturada não contém binários: recuperação completa exige backup do banco. Mídias referenciadas em versões não podem ser removidas isoladamente, preservando histórico.

Leitor mostra páginas duplas acima de 1000 px e página única abaixo disso, sumário, busca textual, virada por controles/teclado com animação CSS, numeração e sombras. Interações dentro das páginas não ativam virada por gesto. Há modo vertical sem animação e respeito a redução de movimento. Não foi necessária instalação de wrapper React de terceiros. O leitor não impõe altura fixa que oculte conteúdo.

Conclusão de páginas, marcadores, tentativas de quiz e última página ficam no servidor, com revisão para impedir sobrescrita entre abas. Anotações privadas têm criação e exclusão explícitas. Narração usa voz selecionada, com pausa/retomada/parada e limite declarado de 3.000 caracteres por acionamento. Narrar ao mudar página é opcional; não há avanço automático. Voz neural natural permanece pendente conforme `SALY_VOICE_PROVIDERS.md`.

Tutoria prepara livro/capítulo/página/trecho/fontes no campo de conversa mediante confirmação. O texto é dado não confiável para comandos; publicação não é uma ferramenta do modelo. A proprietária revisa e envia, com o consentimento remoto existente. Preparar o campo não chama Groq. A conexão atual não foi testada com credenciais aqui.

Imagens de capa/páginas usam upload privado normalizado. Os contratos permitem áudio/vídeo privados; seu upload depende da etapa multimídia e não é anunciado como disponível antes dela. Microscópio, célula, DNA e ecologia recebem motores didáticos na fase de Biologia. Modelos 3D não são necessários ao fallback 2D; não há modelo anatômico 3D instalado. A cópia de livros no cofre é uma extensão separada; a primeira versão do leitor depende de rede.

Verificação: três testes Python de domínio e `scripts/browser_library.py` com Chromium real passaram, cobrindo autoria, páginas duplas/únicas, progresso, notas, última página, publicação e contexto sem envio. Não comprova revisão científica da proprietária ou Android físico.

## Edição inicial de Biologia

Na fase 6, o primeiro início cria uma única edição **draft**, com nove páginas originais, capítulos 1–4 iniciais, prévia do capítulo 6 e sumário planejado dos demais. A instalação é idempotente; excluir o livro não o recria. A autoria assistida está declarada, e nenhuma publicação ocorre automaticamente. Fontes são referências bibliográficas, sem copiar textos/imagens de Campbell, Alberts ou OpenStax. Consulta online atual e revisão científica editorial não foram certificadas; datas de verificação permanecem nulas.

Atividades implementadas: célula 2D com seleção e distinção entre tipos animal/vegetal/procarionte; DNA com complemento antiparalelo/RNA da fita codificante, substituição e cruzamento mendeliano de um locus; modelo logístico com gráfico/tabela e hipóteses explícitas; quizzes com tentativas persistentes; microscópio esquemático com zoom, foco e iluminação digitais. Não há micrografias licenciadas, escala física calibrada, previsão ecológica real ou modelo anatômico 3D. Esse alcance é deliberadamente identificado na interface. As atividades não executam código fornecido pelo livro.

Três testes Vitest adicionais verificam regras de DNA, cruzamentos e comportamento de equilíbrio/capacidade da logística. Um teste Python verifica o rascunho validado, instalação idempotente e ausência de recriação após exclusão. `browser_biology.py` passou com interações reais e contexto do elemento preparado na conversa sem envio remoto; layout móvel sem erros de página.

## Extensões de mídia e offline

Áudio/vídeo privados podem ser enviados pelo editor com FFmpeg disponível, vinculados ao livro e validados por tipo. O leitor usa reprodução nativa real. No cofre, escolha livro/edição e opcionalmente mídias até 5 MB cada; hashes são conferidos e bytes ficam criptografados. A leitura offline usa URLs Blob locais, sem buscar a API ou imagens externas. Progresso e novas notas persistem offline e sincronizam ao abrir/reconectar, com conflitos explícitos e notas idempotentes. Edição editorial continua online; não se inventa publicação offline. Cópia limpa de livro excluído é removida ao sincronizar; rascunho pendente vira conflito para exportar/decidir.

O limite de narração foi alinhado a 3.000 caracteres por acionamento para o contrato do TTS de servidor. Voz de servidor/tutoria remota exigem rede. Não há motor neural instalado no aparelho.
