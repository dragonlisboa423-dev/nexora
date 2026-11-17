import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, put } from "./api";

export default function TextBook() {
  const { documentId } = useParams();
  const [doc, setDoc] = useState<any>(null),
    [page, setPage] = useState(1),
    [error, setError] = useState("");
  const queue = useRef(Promise.resolve());
  useEffect(() => {
    let alive = true;
    Promise.all([
      api(`/knowledge/${documentId}`),
      api(`/knowledge/${documentId}/reading-position`),
    ])
      .then(([d, p]) => {
        if (alive) {
          setDoc(d);
          setPage(Math.max(1, Math.min(p.page, d.pages?.length || 1)));
        }
      })
      .catch((e) => setError(e.message));
    return () => {
      alive = false;
    };
  }, [documentId]);
  function turn(value: number) {
    const next = Math.max(1, Math.min(value, doc.pages.length));
    setPage(next);
    queue.current = queue.current
      .catch(() => {})
      .then(() =>
        put(`/knowledge/${documentId}/reading-position`, { page: next }),
      )
      .catch((e) => setError(e.message));
  }
  const section = doc?.pages?.[page - 1];
  return (
    <section className="text-book card">
      <Link to="/knowledge">← Centro Smolin</Link>
      {error && <p role="alert">{error}</p>}
      <h1>{doc?.title || doc?.name || "Abrindo texto…"}</h1>
      <p>{doc?.author || "Autoria não informada"}</p>
      <p>
        Leitura do texto extraído. Imagens, tabelas e diagramação permanecem no
        arquivo original.
      </p>
      {doc && (
        <>
          <div className="toolbar">
            <button disabled={page <= 1} onClick={() => turn(page - 1)}>
              Capítulo anterior
            </button>
            <select
              aria-label="Capítulo do livro"
              value={page}
              onChange={(e) => turn(Number(e.target.value))}
            >
              {doc.pages?.map((p: any) => (
                <option key={p.page} value={p.page}>
                  {p.label || `Seção ${p.page}`}
                </option>
              ))}
            </select>
            <button
              disabled={page >= doc.pages.length}
              onClick={() => turn(page + 1)}
            >
              Próximo capítulo
            </button>
            <a href={`/api/knowledge/${documentId}/original?download=true`}>
              Baixar original
            </a>
          </div>
          <p role="status">
            Seção {page} de {doc.pages.length}
          </p>
          <article aria-label="Texto do capítulo">
            <h2>{section?.label}</h2>
            <div style={{ whiteSpace: "pre-wrap" }}>{section?.content}</div>
          </article>
        </>
      )}
    </section>
  );
}
