# SALY 2.0 — auditoria e estratégia visual

Especificação de 14.268 bytes recebida e lida integralmente em 17/11/2026 (America/Sao_Paulo). Base: `f03426b`, branch `feat/saly-smolin`; árvore de trabalho limpa antes desta etapa.

## Estado inspecionado antes de modificar o código

- React/TypeScript/Vite; Three e React Three Fiber já renderizam o núcleo por shaders/deformação procedural em `Core.tsx`. Existe fallback 2D e preferência de movimento reduzido. A superfície atual é uma esfera, com toros/partículas e linguagem ciano/tecnológica.
- `main.tsx` reúne conversa, áudio real, consentimento, histórico e cerca de quinze destinos de navegação. Chat/Groq, Core Memory/RAG, permissões e armazenamento permanecem responsabilidades do backend existente.
- `Library.tsx` já tem capítulos, páginas reais, sumário, narração, marcadores, notas, progresso com revisão e edição. PDF.js abre originais e há leitor textual EPUB. Faltam gestos de virada e apresentação editorial mais clara.
- `Personal.tsx` tem compras em centavos, orçamento, categorias, revisão/conferência, comprovantes privados e alarmes. Não existe foto de produto independente do comprovante nem metas de economia persistentes. Não se pode apresentar um comprovante como se fosse a foto do produto.
- `Studio.tsx` já edita imagens e monta vídeos com FFmpeg, conserva galeria/jobs/download/cancelamento e reporta provedores generativos indisponíveis. Exibe muita configuração técnica antes da criação.
- Memórias, Smolin e Biblioteca possuem rotas e mecanismos de exclusão/autorização próprios. Espaço guarda links/gavetas; Atividades e Avaliação/Laboratório são inspeção técnica; vozes são preferências/prévias. Todos serão acessíveis em suas áreas ou em Ajustes, sem exclusão de dados.
- PWA/cofre cifrado, histórico offline escolhido e cache público versionado já existem. Preservar APIs privadas fora do cache e lazy loading; testar desktop e viewport móvel sem alegar Android físico.

## Mapa de navegação previsto

Conversa `/`; Conhecimento `/knowledge` (Centro Memorial, memórias, Smolin em `/knowledge/documents`, livros, Espaço); Mídia `/studio`; Rotina `/routine` (agenda, alarmes, compras, desejos e finanças). Configurações, vozes, ferramentas, inspeção e diagnóstico permanecem em `/advanced`/rotas existentes. URLs de memórias, livros, agenda, alarmes e leitores de documento continuam funcionando. A mudança de `/knowledge` para a entrada unificada é intencional; arquivos/API/IDs de documento não mudam.

## Preservação e limites

Nenhum banco, memória, modelo, chave ou `.env` será substituído. Não há migração destrutiva. Fotos de produto usarão o armazenamento privado e a quota existentes, em um vínculo diferente de comprovantes; metas manuais serão configuração versionada adicional. Atualização/exclusão de compra deve conservar/remover ambos os vínculos corretamente, e exportações não carregarão ponteiros privados inválidos. Não será chamado provedor pago ou automático de geração.

O coração reutiliza R3F, clock, estados reais, sinal PCM/RMS e deformação por shader; troca a geometria esférica por tecidos paramétricos, folhas curvas e tubos ramificados combinados. Qualidade leve, movimento reduzido, pausa fora da tela e fallback vetorial serão verificados. A aparência botânica é ficcional, não medição biológica nem alegação de consciência.

## Verificação prevista

Capturas antes/depois, navegação de quatro áreas, histórico em gaveta, rotas legadas acessíveis, estados do núcleo e qualidade 2D/reduzida, leitura/gesto/progresso/biologia preservados, fotos privadas e gráficos baseados em registros, metas persistentes, montagem/galeria reais, consentimento/erros, mobile/PWA/offline e regressões. Medir carregamento, frames e custo de renderização em Chromium; resultados são daquele ambiente, sem extrapolar para Android físico.
