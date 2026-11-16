# Espaço — gavetas de links

Gavetas têm nome, cor, ícone e posição. Links manuais têm título, URL, descrição, gaveta, etiquetas, posição e favorito. A interface permite criar, editar, mover entre gavetas, ordenar pela posição, pesquisar etiquetas e filtrar favoritos. Excluir uma gaveta pede confirmação e exclui seus links na mesma transação. Exportar/importar usa `saly-space-v1`; importação é aditiva, remapeia IDs e valida tudo antes de concluir. Uma entrada inválida reverte toda a importação.

Somente HTTPS é aceito por padrão. HTTP exige permissão explícita por link. São recusados esquemas executáveis, credenciais, barras invertidas, espaços/controles e portas inválidas. Links abrem com `noopener noreferrer` e sem referenciador. Nenhum site é visitado automaticamente, nem há extração de conteúdo ou credenciais. A validação do esquema não certifica reputação do destino.

O cofre criptografado oferece cópia e edição offline mediante autorização separada. Links externos continuam dependentes de rede. A fila sincroniza criação de gaveta antes de links criados depois, com IDs estáveis; conflitos e exclusões exigem revisão. Exclusões em cascata geram tombstones para os links, evitando cópias órfãs após sincronizar. Clientes antigos continuam recebendo apenas memórias, lembretes e documentos: novos tipos exigem o parâmetro `kinds` explícito no bootstrap/pull.
