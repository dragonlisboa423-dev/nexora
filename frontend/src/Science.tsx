import { useState } from "react";
import { cross, dna, ecology } from "./science";
type Data = Record<string, any>;
const structures: Record<
  string,
  { name: string; description: string; relation: string }
> = {
  membrane: {
    name: "Membrana plasmática",
    description:
      "Bicamada lipídica com proteínas. Delimita a célula e participa de transporte e comunicação.",
    relation:
      "Trocas com o citoplasma dependem da permeabilidade e de transportadores.",
  },
  cytoplasm: {
    name: "Citoplasma",
    description:
      "Inclui citosol e estruturas celulares fora do núcleo, quando há núcleo.",
    relation:
      "Muitas reações metabólicas ocorrem no citosol; não é apenas um preenchimento inerte.",
  },
  nucleus: {
    name: "Núcleo",
    description:
      "Compartimento com envoltório que abriga a maior parte do DNA de células eucarióticas.",
    relation:
      "A transcrição produz RNAs; parte deles orienta síntese proteica nos ribossomos.",
  },
  mitochondria: {
    name: "Mitocôndria",
    description:
      "Organela envolvida em respiração celular e outras funções metabólicas. Possui DNA próprio.",
    relation:
      "Também existe em células vegetais. ATP não é produzido exclusivamente nesta organela.",
  },
  er: {
    name: "Retículo endoplasmático",
    description:
      "Rede de membranas envolvida na síntese e processamento de moléculas.",
    relation:
      "O retículo rugoso associa ribossomos; proteínas podem seguir para o Golgi.",
  },
  golgi: {
    name: "Complexo de Golgi",
    description:
      "Participa da modificação, triagem e transporte de proteínas e lipídios.",
    relation: "Recebe materiais do retículo e os direciona por vesículas.",
  },
  ribosomes: {
    name: "Ribossomos",
    description:
      "Complexos de RNA e proteínas que traduzem RNA mensageiro em polipeptídios.",
    relation: "Presentes em procariontes e eucariontes; não possuem membrana.",
  },
  wall: {
    name: "Parede celular",
    description:
      "Camada externa de suporte. Nas plantas, é rica em celulose; a composição varia entre outros grupos.",
    relation:
      "Não substitui a membrana plasmática e não está presente nas células animais.",
  },
  chloroplast: {
    name: "Cloroplasto",
    description:
      "Organela fotossintética em células apropriadas de plantas e algas.",
    relation:
      "Nem toda célula vegetal tem cloroplastos; células de muitas raízes são exemplo.",
  },
  vacuole: {
    name: "Vacúolo central",
    description:
      "Compartimento de armazenamento e regulação, frequentemente grande em células vegetais maduras.",
    relation:
      "Participa da manutenção do turgor em conjunto com a parede celular.",
  },
  nucleoid: {
    name: "Nucleoide",
    description:
      "Região onde se concentra DNA de uma célula procariótica, sem envoltório nuclear.",
    relation:
      "Procariontes também têm ribossomos e membrana, mas não núcleo nem mitocôndrias.",
  },
};
function Cell({ config, onAsk }: { config: Data; onAsk: (s: string) => void }) {
  const [type, setType] = useState(config.cell_type ?? "animal"),
    [selected, setSelected] = useState("membrane");
  const keys =
    type === "prokaryote"
      ? ["membrane", "cytoplasm", "nucleoid", "ribosomes"]
      : [
          "membrane",
          "cytoplasm",
          "nucleus",
          "mitochondria",
          "er",
          "golgi",
          "ribosomes",
          ...(type === "plant" ? ["wall", "chloroplast", "vacuole"] : []),
        ];
  const item = structures[selected] ?? structures.membrane;
  const color = (key: string) => (selected === key ? "#e4e6a5" : "#71c9b5");
  return (
    <section className="science-block">
      <h3>Célula explorável</h3>
      <label>
        Tipo celular
        <select
          aria-label="Tipo celular"
          value={type}
          onChange={(e) => {
            setType(e.target.value);
            setSelected("membrane");
          }}
        >
          <option value="animal">Eucariótica animal</option>
          <option value="plant">Eucariótica vegetal</option>
          <option value="prokaryote">Procariótica</option>
        </select>
      </label>
      <svg
        viewBox="0 0 420 280"
        role="img"
        aria-label={`Esquema de célula ${type}; estruturas selecionáveis nos botões abaixo`}
      >
        <title>
          Esquema original simplificado; formas e tamanhos não estão em escala
        </title>
        {type === "plant" && (
          <rect
            x="18"
            y="12"
            width="385"
            height="250"
            rx="35"
            fill="none"
            stroke={color("wall")}
            strokeWidth="8"
          />
        )}
        <ellipse
          cx="210"
          cy="140"
          rx={type === "prokaryote" ? 170 : 175}
          ry={type === "prokaryote" ? 85 : 115}
          fill="#153d3b"
          stroke={color("membrane")}
          strokeWidth="4"
        />
        {type === "prokaryote" ? (
          <path
            d="M130 120Q210 60 280 120T160 170T260 145"
            fill="none"
            stroke={color("nucleoid")}
            strokeWidth="6"
          />
        ) : (
          <>
            <ellipse
              cx="155"
              cy="132"
              rx="48"
              ry="42"
              fill="#294b67"
              stroke={color("nucleus")}
              strokeWidth="4"
            />
            <ellipse cx="164" cy="136" rx="12" ry="10" fill="#78a9bc" />
            <path
              d="M210 95Q245 55 260 105M210 110Q250 65 272 117M210 125Q255 88 280 132"
              fill="none"
              stroke={color("er")}
              strokeWidth="5"
            />
            <path
              d="M250 180q35 -20 50 0m-47 9q32 -20 47 0m-42 8q27 -18 40 0"
              stroke={color("golgi")}
              fill="none"
              strokeWidth="5"
            />
            {[
              [87, 180],
              [290, 67],
            ].map(([x, y]) => (
              <g key={x}>
                <ellipse
                  cx={x}
                  cy={y}
                  rx="25"
                  ry="13"
                  fill="#634d35"
                  stroke={color("mitochondria")}
                  strokeWidth="3"
                />
                <path
                  d={`M${x - 15} ${y}l7 -6 8 12 8 -12 7 6`}
                  fill="none"
                  stroke="#d1bc85"
                />
              </g>
            ))}
            {type === "plant" && (
              <>
                <ellipse
                  cx="245"
                  cy="145"
                  rx="50"
                  ry="31"
                  fill="#2a6575"
                  opacity=".55"
                  stroke={color("vacuole")}
                  strokeWidth="3"
                />
                <ellipse
                  cx="320"
                  cy="125"
                  rx="24"
                  ry="14"
                  fill="#32744e"
                  stroke={color("chloroplast")}
                  strokeWidth="3"
                />
              </>
            )}
          </>
        )}
        {Array.from({ length: 12 }, (_, i) => (
          <circle
            key={i}
            cx={65 + ((i * 43) % 290)}
            cy={55 + ((i * 31) % 175)}
            r="3"
            fill={color("ribosomes")}
          />
        ))}
      </svg>
      <p>
        Modelo 2D original, sem escala. Algumas estruturas foram omitidas; tipos
        celulares não representam todos os tecidos ou grupos.
      </p>
      <div className="toolbar">
        {keys.map((key) => (
          <button
            key={key}
            aria-pressed={selected === key}
            onClick={() => setSelected(key)}
          >
            {structures[key].name}
          </button>
        ))}
      </div>
      <h4>{item.name}</h4>
      <p>{item.description}</p>
      <p>{item.relation}</p>
      <button
        onClick={() =>
          onAsk(`${type}: ${item.name}. ${item.description} ${item.relation}`)
        }
      >
        Perguntar sobre {item.name}
      </button>
    </section>
  );
}
function DnaLab({
  config,
  onAsk,
}: {
  config: Data;
  onAsk: (s: string) => void;
}) {
  const [sequence, setSequence] = useState(config.sequence ?? "ATGCCATTA"),
    [position, setPosition] = useState(1),
    [base, setBase] = useState("A"),
    [a, setA] = useState("Aa"),
    [b, setB] = useState("Aa");
  let result;
  try {
    result = dna(sequence);
  } catch {}
  const children = cross(a, b);
  return (
    <section className="science-block">
      <h3>Laboratório de DNA</h3>
      <label>
        Fita codificante 5′ → 3′
        <input
          maxLength={60}
          value={sequence}
          onChange={(e) => setSequence(e.target.value.toUpperCase())}
        />
      </label>
      {result ? (
        <>
          <p className="dna-string">Codificante 5′ {result.coding} 3′</p>
          <p className="dna-string">Complementar 3′ {result.complement} 5′</p>
          <p className="dna-string">RNA 5′ {result.rna} 3′</p>
          <p>
            O RNA mostrado corresponde à fita codificante com U no lugar de T.
            Modelo sem íntrons, processamento de RNA ou tradução.
          </p>
          <div className="toolbar">
            <label>
              Posição da substituição
              <input
                type="number"
                min="1"
                max={sequence.length}
                value={position}
                onChange={(e) => setPosition(Number(e.target.value))}
              />
            </label>
            <label>
              Nova base
              <select
                aria-label="Nova base"
                value={base}
                onChange={(e) => setBase(e.target.value)}
              >
                {[..."ACGT"].map((base) => (
                  <option key={base}>{base}</option>
                ))}
              </select>
            </label>
            <button
              disabled={position < 1 || position > sequence.length}
              onClick={() =>
                setSequence(
                  sequence.slice(0, position - 1) +
                    base +
                    sequence.slice(position),
                )
              }
            >
              Aplicar substituição
            </button>
          </div>
        </>
      ) : (
        <p role="alert">Use somente 1 a 60 bases A, C, G ou T.</p>
      )}
      <h4>Herança mendeliana simplificada</h4>
      <div className="toolbar">
        {[
          [a, setA, "Genótipo parental A"],
          [b, setB, "Genótipo parental B"],
        ].map(([value, set, label]) => (
          <label key={label as string}>
            {label as string}
            <select
              aria-label={label as string}
              value={value as string}
              onChange={(e) => (set as (s: string) => void)(e.target.value)}
            >
              {["AA", "Aa", "aa"].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
        ))}
      </div>
      <p>Combinações equiprováveis: {children.join(" · ")}.</p>
      <p>
        Um locus, segregação igual e ausência de seleção. Não representa toda a
        herança humana nem implica que dominante significa melhor.
      </p>
      <button
        onClick={() =>
          onAsk(
            `DNA codificante ${sequence}; cruzamento didático ${a} × ${b}: ${children.join(", ")}.`,
          )
        }
      >
        Perguntar sobre este DNA
      </button>
    </section>
  );
}
function Ecology({
  config,
  onAsk,
}: {
  config: Data;
  onAsk: (s: string) => void;
}) {
  const [initial, setInitial] = useState(config.initial_population ?? 20),
    [capacity, setCapacity] = useState(config.capacity ?? 100),
    [rate, setRate] = useState(config.growth_rate ?? 0.15),
    [temperature, setTemperature] = useState(25),
    [light, setLight] = useState(100),
    [nutrients, setNutrients] = useState(100),
    [values, setValues] = useState<number[]>([]);
  const effective =
    rate *
    Math.exp(-(((temperature - 25) / 15) ** 2)) *
    (light / 100) *
    (nutrients / 100);
  const max = Math.max(capacity, ...values, 1);
  return (
    <section className="science-block">
      <h3>Ecossistema didático</h3>
      <p>
        Uma população fechada, crescimento logístico contínuo amostrado em 30
        passos abstratos. Recursos fixos; sem predação, migração ou evolução.
        Temperatura ótima 25 °C e resposta gaussiana são hipóteses deste modelo,
        sem calibração experimental.
      </p>
      <div className="form-grid">
        {[
          ["População inicial", initial, setInitial, 0, 1000, 1],
          ["Capacidade de suporte", capacity, setCapacity, 1, 1000, 1],
          ["Taxa por passo", rate, setRate, 0, 1, 0.01],
          ["Temperatura do cenário", temperature, setTemperature, 0, 50, 1],
          ["Luz relativa (%)", light, setLight, 0, 100, 1],
          ["Nutrientes relativos (%)", nutrients, setNutrients, 0, 100, 1],
        ].map(([label, value, set, min, max, step]) => (
          <label key={label as string}>
            {label as string}: {value as number}
            <input
              aria-label={label as string}
              type="range"
              min={min as number}
              max={max as number}
              step={step as number}
              value={value as number}
              onChange={(e) => {
                (set as (n: number) => void)(Number(e.target.value));
                setValues([]);
              }}
            />
          </label>
        ))}
      </div>
      <p>Taxa efetiva calculada: {effective.toFixed(4)} por passo.</p>
      <button onClick={() => setValues(ecology(initial, capacity, effective))}>
        Executar cenário
      </button>
      {values.length > 0 && (
        <>
          <svg
            role="img"
            aria-label="População calculada ao longo de 30 passos"
            viewBox="0 0 400 220"
          >
            <path d="M35 10V190H390" fill="none" stroke="#abc9bd" />
            <polyline
              fill="none"
              stroke="#8ae6cc"
              strokeWidth="3"
              points={values
                .map(
                  (v, i) => `${35 + (i * 350) / 30},${190 - (v / max) * 170}`,
                )
                .join(" ")}
            />
            <text x="36" y="215" fill="currentColor">
              0 · passos abstratos · 30
            </text>
            <text x="2" y="18" fill="currentColor">
              {Math.round(max)}
            </text>
          </svg>
          <p>
            População esperada final: {values.at(-1)!.toFixed(2)}; valor do
            modelo, não contagem observada.
          </p>
          <details>
            <summary>Tabela de resultados</summary>
            <table>
              <thead>
                <tr>
                  <th>Passo</th>
                  <th>População esperada</th>
                </tr>
              </thead>
              <tbody>
                {values.map((v, i) => (
                  <tr key={i}>
                    <td>{i}</td>
                    <td>{v.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
          <button
            onClick={() =>
              onAsk(
                `Cenário didático: N0=${initial}, K=${capacity}, r efetivo=${effective.toFixed(4)}, N30=${values.at(-1)!.toFixed(3)}; sem calibração real.`,
              )
            }
          >
            Perguntar sobre este cenário
          </button>
        </>
      )}
    </section>
  );
}
function Microscope({
  config,
  onAsk,
}: {
  config: Data;
  onAsk: (s: string) => void;
}) {
  const [slide, setSlide] = useState(config.slide ?? "plant_schema"),
    [zoom, setZoom] = useState(1),
    [focus, setFocus] = useState(50),
    [light, setLight] = useState(100);
  return (
    <section className="science-block">
      <h3>Microscópio virtual — esquema didático</h3>
      <p>
        Desenhos vetoriais originais, sem micrografia externa. Zoom digital não
        aumenta resolução óptica. A escala física em µm não foi calibrada e não
        será inventada.
      </p>
      <label>
        Lâmina esquemática
        <select
          aria-label="Lâmina esquemática"
          value={slide}
          onChange={(e) => setSlide(e.target.value)}
        >
          <option value="plant_schema">Tecido vegetal esquemático</option>
          <option value="animal_schema">Células animais esquemáticas</option>
        </select>
      </label>
      <div className="microscope-field">
        <svg
          viewBox="0 0 300 300"
          role="img"
          aria-label="Campo visual esquemático com zoom, foco e iluminação digitais"
        >
          <defs>
            <clipPath id={`field-${slide}`}>
              <circle cx="150" cy="150" r="140" />
            </clipPath>
          </defs>
          <g clipPath={`url(#field-${slide})`}>
            <rect width="300" height="300" fill="#8aab8c" />
            <g
              style={{
                filter: `blur(${Math.abs(focus - 50) / 12}px) brightness(${light / 100})`,
                transform: `translate(150px,150px) scale(${zoom}) translate(-150px,-150px)`,
              }}
            >
              {Array.from({ length: 25 }, (_, i) => {
                const x = (i % 5) * 65 - 10,
                  y = Math.floor(i / 5) * 65 - 10;
                return (
                  <g key={i}>
                    {slide === "plant_schema" ? (
                      <rect
                        x={x}
                        y={y}
                        width="62"
                        height="62"
                        rx="6"
                        fill="#578554"
                        stroke="#284b35"
                        strokeWidth="3"
                      />
                    ) : (
                      <ellipse
                        cx={x + 30}
                        cy={y + 30}
                        rx="28"
                        ry="24"
                        fill="#b69ca9"
                        stroke="#6c586b"
                        strokeWidth="2"
                      />
                    )}
                    <ellipse
                      cx={x + 33}
                      cy={y + 30}
                      rx="8"
                      ry="6"
                      fill="#31455c"
                    />
                  </g>
                );
              })}
            </g>
          </g>
          <circle
            cx="150"
            cy="150"
            r="140"
            fill="none"
            stroke="#b4d7c8"
            strokeWidth="5"
          />
        </svg>
      </div>
      <div className="form-grid">
        {[
          ["Zoom digital", zoom, setZoom, 1, 4, 0.1],
          ["Foco didático", focus, setFocus, 0, 100, 1],
          ["Iluminação digital (%)", light, setLight, 30, 180, 1],
        ].map(([label, value, set, min, max, step]) => (
          <label key={label as string}>
            {label as string}: {value as number}
            <input
              aria-label={label as string}
              type="range"
              min={min as number}
              max={max as number}
              step={step as number}
              value={value as number}
              onChange={(e) =>
                (set as (n: number) => void)(Number(e.target.value))
              }
            />
          </label>
        ))}
      </div>
      <p>
        Contornos representam limites celulares; elipses escuras representam
        núcleos. A aparência é ilustrativa e omite membranas internas e muitas
        estruturas.
      </p>
      <button
        onClick={() =>
          onAsk(
            `Microscópio esquemático ${slide}, zoom digital ${zoom}×; sem calibração física ou micrografia real.`,
          )
        }
      >
        Perguntar sobre microscopia
      </button>
    </section>
  );
}
export function ScienceBlock({
  block,
  onAsk,
}: {
  block: Data;
  onAsk: (s: string) => void;
}) {
  if (block.type === "cellViewer") return <Cell config={block} onAsk={onAsk} />;
  if (block.type === "dnaLab") return <DnaLab config={block} onAsk={onAsk} />;
  if (block.type === "ecologyLab")
    return <Ecology config={block} onAsk={onAsk} />;
  if (block.type === "microscope")
    return <Microscope config={block} onAsk={onAsk} />;
  return <p>Componente científico indisponível.</p>;
}
