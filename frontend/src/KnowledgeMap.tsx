import { useState } from "react";
import { api } from "./api";

export function KnowledgeMap({ notify }: { notify: (s: string) => void }) {
  const [graph, setGraph] = useState<any>(null),
    [selected, setSelected] = useState<any>(null),
    [query, setQuery] = useState(""),
    [busy, setBusy] = useState(false),
    [zoom, setZoom] = useState(1);
  async function load() {
    setBusy(true);
    try {
      setGraph(await api("/knowledge/map?q=" + encodeURIComponent(query)));
      setSelected(null);
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const nodes = graph?.nodes ?? [];
  const positions = new Map<string, { x: number; y: number }>(
    nodes.map((n: any, i: number) => [
      n.id,
      {
        x: 450 + 340 * Math.cos((2 * Math.PI * i) / Math.max(1, nodes.length)),
        y: 300 + 230 * Math.sin((2 * Math.PI * i) / Math.max(1, nodes.length)),
      },
    ]),
  );
  return (
    <details
      className="card knowledge-map"
      onToggle={(e) => {
        if (e.currentTarget.open && !graph && !busy) void load();
      }}
    >
      <summary>Mapa de conhecimento com fontes</summary>
      <p>
        Conceitos sugeridos por termos e coocorrência nos trechos. Uma linha não
        comprova causalidade, concordância entre autores ou retreinamento da IA.
      </p>
      <form
        className="toolbar"
        onSubmit={(e) => {
          e.preventDefault();
          void load();
        }}
      >
        <input
          aria-label="Filtrar conceitos do mapa"
          value={query}
          maxLength={300}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Genética, evolução…"
        />
        <button disabled={busy}>
          {busy ? "Lendo índice…" : "Atualizar mapa"}
        </button>
      </form>
      {graph && (
        <>
          <small>
            {graph.covered_chunks} trechos examinados
            {graph.limited
              ? " · cobertura limitada aos primeiros 1.000 trechos"
              : ""}
            . Novas importações aparecem ao atualizar.
          </small>
          <label>
            Zoom do mapa
            <input
              aria-label="Zoom do mapa"
              type="range"
              min="0.7"
              max="2"
              step="0.1"
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
            />
          </label>
          {!nodes.length ? (
            <p>
              Nenhum conceito disponível nesta seleção. Importe e processe
              documentos.
            </p>
          ) : (
            <div className="graph-scroll">
              <svg
                viewBox="0 0 900 600"
                style={{ width: `${zoom * 100}%`, minWidth: 620 }}
                aria-label="Grafo de conceitos com fontes"
              >
                {graph.edges.map((edge: any) => {
                  const a = positions.get(edge.source),
                    b = positions.get(edge.target);
                  return a && b ? (
                    <line
                      key={edge.source + ":" + edge.target}
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      stroke="var(--accent, #9ee7db)"
                      opacity="0.15"
                    />
                  ) : null;
                })}
                {nodes.map((node: any) => {
                  const p = positions.get(node.id)!;
                  return (
                    <g
                      key={node.id}
                      transform={`translate(${p.x},${p.y})`}
                      role="button"
                      pointerEvents="bounding-box"
                      tabIndex={0}
                      aria-label={`Conceito ${node.label}`}
                      onClick={() => setSelected(node)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setSelected(node);
                        }
                      }}
                    >
                      <circle
                        r={selected?.id === node.id ? 12 : 8}
                        fill="#9ee7db"
                      />
                      <text
                        y="-15"
                        textAnchor="middle"
                        fill="#d9ecec"
                        fontSize="13"
                      >
                        {node.label}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          )}
          <div className="toolbar" aria-label="Lista acessível de conceitos">
            {nodes.map((node: any) => (
              <button
                className="secondary"
                key={node.id}
                onClick={() => setSelected(node)}
              >
                {node.label}
              </button>
            ))}
          </div>
          {selected && (
            <section aria-label="Fontes do conceito">
              <h3>{selected.label}</h3>
              <p>
                Ocorrências: {selected.occurrences}. Consulte os trechos para
                interpretar o conceito no contexto dos autores.
              </p>
              {selected.sources.map((source: any) => (
                <blockquote key={source.chunk_id}>
                  <p>{source.excerpt}</p>
                  <a href={source.url} target="_blank" rel="noreferrer">
                    {source.name} · {source.author} ·{" "}
                    {source.label || `página/seção ${source.page}`}
                  </a>
                </blockquote>
              ))}
              <h4>Conexões documentadas</h4>
              {graph.edges
                .filter(
                  (e: any) =>
                    e.source === selected.id || e.target === selected.id,
                )
                .map((edge: any) => (
                  <p key={edge.source + edge.target}>
                    {edge.source} ↔ {edge.target} · {edge.count} trechos ·
                    coocorrência, sem conclusão causal
                  </p>
                ))}
            </section>
          )}
          {graph.contrast_candidates.length > 0 && (
            <section>
              <h3>Contrastes a revisar</h3>
              {graph.contrast_candidates.map((c: any, i: number) => (
                <p key={i}>
                  {c.concepts.join(" ↔ ")}: {c.review}{" "}
                  {c.sources.map((s: any) => (
                    <a
                      key={s.chunk_id}
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {" "}
                      {s.name}
                    </a>
                  ))}
                </p>
              ))}
            </section>
          )}
        </>
      )}
    </details>
  );
}
