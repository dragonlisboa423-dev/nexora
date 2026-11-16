"""Original initial teaching edition. Never auto-published or reinstalled after deletion."""

from . import storage as store
from .library import save_book

REFERENCE = {
    "title": "Campbell Biology, 12ª ed. (2020), capítulos introdutórios",
    "url": "",
    "author": "Urry, Cain, Wasserman, Minorsky e Orr",
    "license": "Referência bibliográfica; nenhum texto ou imagem do livro foi incorporado",
    "checked_on": None,
}
CELL_REFERENCE = {
    "title": "Molecular Biology of the Cell, 7ª ed. (2022)",
    "url": "",
    "author": "Alberts e colaboradores",
    "license": "Referência bibliográfica; nenhum texto ou imagem do livro foi incorporado",
    "checked_on": None,
}
DNA_REFERENCE = {
    "title": "Molecular Structure of Nucleic Acids: A Structure for Deoxyribose Nucleic Acid (1953)",
    "url": "https://doi.org/10.1038/171737a0",
    "author": "J. D. Watson e F. H. C. Crick",
    "license": "Referência ao artigo; conteúdo não reproduzido",
    "checked_on": None,
}


def text(value):
    return {"type": "text", "text": value}


def page(key, title, *blocks, sources=None):
    return {"id": key, "title": title, "blocks": list(blocks), "sources": sources or [REFERENCE]}


def quiz(question, choices, index, explanation):
    return {
        "type": "quiz",
        "question": question,
        "choices": choices,
        "correct_index": index,
        "explanation": explanation,
    }


def initial_book():
    return {
        "title": "Biologia — Volume I: Fundamentos da Vida",
        "subtitle": "Edição inicial · rascunho para revisão",
        "subject": "Biologia",
        "description": "Texto original introdutório e experiências didáticas. Primeiros quatro capítulos em desenvolvimento; demais capítulos planejados. Não é enciclopédia concluída nem revisão científica certificada.",
        "author": "Texto inicial elaborado com auxílio do Codex; revisão editorial da proprietária pendente",
        "license": "Texto e esquemas originais preparados para o projeto; referências apenas bibliográficas. Publicação e licença final dependem da proprietária.",
        "publication_status": "draft",
        "chapters": [
            {
                "id": "bio-c1",
                "title": "1 — O que é a vida?",
                "description": "Organização, metabolismo, homeostase, hereditariedade e evolução.",
                "pages": [
                    page(
                        "bio-p1",
                        "Vida: um conjunto de processos",
                        text("""## Uma pergunta com fronteiras
Uma pedra cresce quando minerais se depositam sobre ela. Uma chama consome combustível e se propaga. Esses exemplos mostram por que uma única característica, isoladamente, não define vida. A Biologia compara conjuntos de propriedades e investiga como elas se relacionam.

Os organismos conhecidos têm organização celular. Reações químicas transformam matéria e energia: esse conjunto de processos é o metabolismo. Mecanismos de regulação mantêm condições internas dentro de intervalos compatíveis com o funcionamento do organismo, fenômeno chamado homeostase. Isso não significa que o interior permaneça imóvel ou perfeitamente constante.

A reprodução contribui para a continuidade de linhagens, mas não é uma exigência que cada indivíduo precise cumprir para estar vivo. Uma mula estéril continua sendo um animal vivo. Informação hereditária e variação tornam possível a evolução de populações ao longo das gerações; indivíduos não evoluem por necessidade durante a própria vida.

**Exemplo:** uma semente pode apresentar metabolismo muito reduzido e ainda conservar capacidade de germinar. Avaliar vida exige contexto e evidências, não apenas observar movimento.

**Termos:** célula, metabolismo, homeostase, linhagem, população.

**Questão aberta:** quais observações distinguiriam uma semente viável de outra que perdeu a viabilidade? Evite destruir a amostra antes de formular seu teste."""),
                        quiz(
                            "Qual afirmação é mais adequada?",
                            [
                                "Todo indivíduo vivo precisa se reproduzir.",
                                "Uma característica isolada sempre basta para definir vida.",
                                "A reprodução sustenta linhagens, mas um indivíduo estéril pode estar vivo.",
                            ],
                            2,
                            "Características precisam ser avaliadas em conjunto. Esterilidade individual não elimina organização celular, metabolismo e outras propriedades.",
                        ),
                    ),
                    page(
                        "bio-p2",
                        "Escalas de organização e casos limítrofes",
                        text("""## Do componente ao sistema
Moléculas participam de estruturas celulares; células formam organismos unicelulares ou integram organismos multicelulares. Populações da mesma espécie interagem com outras populações em comunidades. Ecossistemas incluem organismos e componentes físicos, como água, luz e solo.

Cada escala permite perguntas diferentes. A composição de uma proteína não explica sozinha toda a dinâmica de uma comunidade. Propriedades de um sistema dependem também das relações entre componentes, sem dispensar mecanismos físicos e químicos.

**Vírus:** possuem material genético e evoluem, mas dependem de células para reproduzir seu genoma e produzir novas partículas; não são células. Sua classificação em relação ao termo “vivo” depende dos critérios explicitados. A controvérsia não autoriza atribuir metabolismo autônomo a uma partícula viral.

**Exercício:** escolha uma lagoa. Identifique uma variável do ambiente, uma população e uma interação. O cenário abaixo é um modelo logístico de uma única população, não uma reprodução completa dessa lagoa."""),
                        {
                            "type": "ecologyLab",
                            "initial_population": 20,
                            "capacity": 100,
                            "growth_rate": 0.15,
                        },
                    ),
                ],
            },
            {
                "id": "bio-c2",
                "title": "2 — Como a Biologia investiga o mundo",
                "description": "Perguntas, hipóteses, variáveis, controles, dados e incerteza.",
                "pages": [
                    page(
                        "bio-p3",
                        "Da observação a um teste",
                        text("""## Formular uma pergunta investigável
Observar que plantas próximas de uma janela crescem de forma diferente pode sugerir uma pergunta: mantendo outras condições semelhantes, a quantidade de luz altera o crescimento desta espécie neste intervalo de tempo?

Uma hipótese é uma explicação provisória que permite prever resultados observáveis. “Luz maior sempre melhora qualquer planta” é ampla demais: espécie, intensidade e disponibilidade de água importam. Uma previsão mais específica compara tratamentos dentro de condições descritas.

Em um experimento, a variável manipulada pode ser o tempo de iluminação; a resposta medida pode ser o aumento de altura. Água, substrato e idade das plantas são possíveis variáveis de controle. Altura não é sinônimo perfeito de saúde nem de biomassa. A escolha da medida delimita o que se pode concluir.

Distribuir plantas entre tratamentos e usar réplicas reduz certas fontes de viés. Medidas repetidas de uma única planta não substituem automaticamente réplicas independentes. Um grupo de comparação ajuda a atribuir diferenças ao tratamento, sem eliminar toda incerteza.

**Prática:** antes de coletar dados, registre pergunta, hipótese, previsão, amostra, procedimento, unidade da medida e critérios de exclusão. Não mude regras silenciosamente depois de ver o resultado."""),
                        quiz(
                            "Qual é a variável resposta no exemplo descrito?",
                            [
                                "Quantidade de água mantida semelhante.",
                                "Aumento de altura medido.",
                                "Tempo de iluminação escolhido como tratamento.",
                            ],
                            1,
                            "A resposta é o resultado medido. A iluminação é manipulada; a água pode ser controlada.",
                        ),
                    ),
                    page(
                        "bio-p4",
                        "Evidência, gráficos e limites",
                        text("""## Concluir na medida dos dados
Uma tabela deve registrar valores, unidades, condições e observações relevantes. Um gráfico permite perceber tendências, mas sua aparência depende da escala e da forma de resumir dados. Uma média sem informação sobre dispersão pode ocultar diferenças importantes.

Correlação, isoladamente, não demonstra causa. Plantas mais altas próximas da janela podem ter recebido também mais água. Experimentos controlados, observações independentes e outras linhas de evidência ajudam a comparar explicações.

Reprodutibilidade inclui descrever métodos e disponibilizar informações suficientes para avaliação. Resultados inesperados devem motivar revisão de procedimentos e hipóteses, sem apagar seletivamente dados inconvenientes. Uma conclusão científica pode mudar diante de evidências melhores.

O cenário computacional desta edição calcula consequências de equações e parâmetros escolhidos. Ele não colhe dados do mundo. Concordar com a própria equação não valida o modelo para uma espécie real.

**Exercício:** desenhe dois gráficos do mesmo conjunto de dados com escalas verticais distintas. Explique o que muda visualmente e o que não muda nos valores. Identifique uma fonte possível de erro e uma decisão que tornaria seu estudo mais transparente."""),
                    ),
                ],
            },
            {
                "id": "bio-c3",
                "title": "3 — A química da vida",
                "description": "Água, interações moleculares e classes de biomoléculas.",
                "pages": [
                    page(
                        "bio-p5",
                        "Água, ligações e ambiente celular",
                        text("""## A matéria viva segue a química
Átomos formam moléculas por interações que dependem de seus elétrons e do ambiente. Ligações covalentes compartilham pares de elétrons; interações não covalentes, como ligações de hidrogênio, contribuem para propriedades da água e para a organização de moléculas biológicas.

A distribuição desigual de cargas na molécula de água contribui para sua polaridade. Água pode interagir com muitos solutos, mas não dissolve igualmente todas as substâncias. Moléculas apolares tendem a se organizar de modo diferente em meio aquoso, comportamento importante para membranas.

O pH está relacionado à atividade de íons hidrogênio e é uma escala logarítmica. Não é correto interpretar uma mudança de uma unidade como mera mudança linear de “um pouco de acidez”. Condições químicas afetam a estrutura e a atividade de moléculas; células regulam ambientes locais, sem mantê-los todos idênticos.

**Exemplo:** uma proteína pode perder sua conformação funcional sob certas mudanças de temperatura ou pH. A resposta depende da proteína e do contexto; não há temperatura universal de desnaturação para todas as proteínas.

**Termos:** polaridade, soluto, ligação de hidrogênio, pH, conformação."""),
                    ),
                    page(
                        "bio-p6",
                        "Biomoléculas e informação",
                        text("""## Estrutura e função
Carboidratos incluem açúcares e polímeros com funções energéticas e estruturais. Lipídios formam um grupo diverso, com componentes de membrana, reservas e moléculas sinalizadoras. Proteínas são polímeros de aminoácidos e exercem funções como catálise, transporte e suporte. Ácidos nucleicos participam do armazenamento, transmissão e uso de informação genética.

Enzimas aceleram reações ao reduzir a barreira de ativação; não criam energia nem tornam qualquer reação termodinamicamente favorável. O funcionamento depende de condições e de interações com outras moléculas.

No DNA de dupla fita, bases se pareiam de modo complementar: A com T e C com G. As fitas são antiparalelas. No RNA, uracila ocupa o papel de base que se pareia com adenina. O exercício abaixo mostra o RNA correspondente à fita codificante; a transcrição real usa a fita molde e envolve proteínas e regulação.

**Exercício:** substitua uma base. A mudança na sequência, por si só, permite concluir que haverá doença? Explique por que contexto, região afetada e processos celulares precisam ser considerados."""),
                        {"type": "dnaLab", "sequence": "ATGCCATTA"},
                        sources=[CELL_REFERENCE, DNA_REFERENCE],
                    ),
                ],
            },
            {
                "id": "bio-c4",
                "title": "4 — Introdução às células",
                "description": "Teoria celular, compartimentos e diversidade.",
                "pages": [
                    page(
                        "bio-p7",
                        "Células: unidade e diversidade",
                        text("""## Um princípio organizador
A teoria celular relaciona organismos a células e à continuidade de células preexistentes. Células compartilham membrana plasmática, material genético e maquinaria de síntese de proteínas, mas variam muito em forma, tamanho e organização.

Procariontes não possuem núcleo delimitado por envoltório; seu DNA se organiza em regiões do citoplasma. Eucariontes possuem núcleo e compartimentos membranosos característicos. Isso não significa que procariontes sejam desorganizados ou “menos evoluídos”. Ambos os grupos têm longa história evolutiva.

Células vegetais e animais são eucarióticas. Plantas possuem mitocôndrias, além de cloroplastos em células fotossintéticas apropriadas. Nem toda célula vegetal contém cloroplastos. Parede celular e vacúolo central são características relevantes, com variação entre tecidos e estágios.

O esquema permite comparar tipos e selecionar estruturas. Posições, cores e tamanhos são didáticos e não descrevem uma célula específica observada ao microscópio."""),
                        {"type": "cellViewer", "cell_type": "animal"},
                        sources=[CELL_REFERENCE],
                    ),
                    page(
                        "bio-p8",
                        "Compartimentos trabalham em conjunto",
                        text("""## Relações importam
Ribossomos traduzem mensagens de RNA em polipeptídios. O retículo endoplasmático e o complexo de Golgi participam da produção, modificação e destinação de muitas moléculas. Mitocôndrias integram processos metabólicos; suas funções não se limitam a uma etiqueta de “usina de energia”.

A membrana separa meios e permite trocas seletivas. Sistemas de transporte, gradientes e sinalização ajudam a coordenar atividades. O núcleo não é um pequeno cérebro da célula: essa metáfora pode esconder as interações químicas que regulam expressão gênica e funcionamento celular.

**Exercício:** acompanhe uma proteína destinada à secreção, do RNA à saída por vesículas. Identifique onde seu percurso é uma simplificação e por que nem toda proteína segue o mesmo caminho.

**Revisão:** explique por que uma bactéria pode produzir proteínas mesmo sem núcleo, retículo ou Golgi."""),
                        quiz(
                            "Qual estrutura participa da síntese de proteínas em procariontes e eucariontes?",
                            ["Cloroplasto.", "Núcleo delimitado por envoltório.", "Ribossomo."],
                            2,
                            "Ribossomos estão presentes nos dois grupos. Procariontes não precisam de núcleo para traduzir RNA.",
                        ),
                        sources=[CELL_REFERENCE],
                    ),
                ],
            },
            {
                "id": "bio-c5",
                "title": "5 — Membranas e transporte",
                "description": "Planejado: difusão, osmose, transporte ativo, gradientes e exemplos. Conteúdo ainda não redigido.",
                "pages": [],
            },
            {
                "id": "bio-c6",
                "title": "6 — Microscopia",
                "description": "Prévia didática; micrografias licenciadas e calibração física pendentes.",
                "pages": [
                    page(
                        "bio-p9",
                        "Observar exige distinguir aumento e resolução",
                        text("""## A imagem não é o objeto
Aumento descreve uma relação entre tamanhos da imagem e do objeto. Resolução se refere à capacidade de distinguir detalhes próximos. Ampliar pixels não recupera informação que não foi capturada.

A observação microscópica depende de iluminação, foco, preparação da amostra e propriedades do instrumento. Uma escala física exige calibração ou metadados confiáveis da aquisição. Sem esses dados, não devemos inventar micrômetros.

O componente abaixo exercita controles com desenhos vetoriais originais. Não é microscópio óptico, micrografia real ou medida de tamanho celular. O desfoque e a iluminação são efeitos digitais para explorar o papel desses controles. Uma edição futura poderá incorporar micrografias com origem, licença e escala verificadas."""),
                        {"type": "microscope", "slide": "plant_schema"},
                    )
                ],
            },
            {
                "id": "bio-c7",
                "title": "7 — Energia e metabolismo",
                "description": "Planejado: ATP, respiração, fotossíntese, fermentação e balanços de matéria/energia.",
                "pages": [],
            },
            {
                "id": "bio-c8",
                "title": "8 — Divisão celular e continuidade da vida",
                "description": "Planejado: ciclo celular, mitose, meiose, cromossomos e hereditariedade.",
                "pages": [],
            },
        ],
    }


def ensure_biology_draft():
    with store.transaction():
        if store.setting("biology_initial_edition") is not None:
            return
        book = save_book(initial_book())
        store.set_setting(
            "biology_initial_edition", {"book_id": book["id"], "status": "draft", "seed_version": 1}
        )
