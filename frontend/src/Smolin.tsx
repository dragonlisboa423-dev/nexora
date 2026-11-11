import { useEffect, useRef, useState } from "react";
import { api, post } from "./api";
import { emit } from "./operations";
import { PageTitle, Empty } from "./Panels";
type Transfer = {
  id: string;
  name: string;
  progress: number;
  status: string;
  error?: string;
};
export function Smolin({
  notify,
  collectionName = "Smoln",
}: {
  notify: (s: string) => void;
  collectionName?: string;
}) {
  const [docs, setDocs] = useState<any[]>([]),
    [jobs, setJobs] = useState<any[]>([]),
    [transfers, setTransfers] = useState<Transfer[]>([]),
    [query, setQuery] = useState(""),
    [results, setResults] = useState<any[]>([]),
    [detail, setDetail] = useState<any>(null);
  const requests = useRef(new Map<string, XMLHttpRequest>()),
    active = useRef(new Set<string>());
  const refresh = async () => {
    try {
      const [d, j] = await Promise.all([
        api("/knowledge"),
        api("/knowledge/jobs"),
      ]);
      setDocs(d);
      setJobs(j);
      const pending = new Set<string>(
        j
          .filter(
            (x: any) =>
              ["processing", "queued"].includes(x.status) && !x.cancelled,
          )
          .map((x: any) => x.id),
      );
      for (const id of pending)
        emit({ type: "DOCUMENT_PROCESSING_STARTED", id });
      for (const id of active.current)
        if (!pending.has(id)) emit({ type: "DOCUMENT_INDEXED", id });
      active.current = pending;
    } catch (e) {
      notify((e as Error).message);
    }
  };
  useEffect(() => {
    void refresh();
    const timer = setInterval(refresh, 2200);
    return () => {
      clearInterval(timer);
      for (const id of active.current) emit({ type: "DOCUMENT_INDEXED", id });
    };
  }, []);
  const update = (id: string, patch: Partial<Transfer>) =>
    setTransfers((items) =>
      items.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    );
  async function upload(files: FileList | File[]) {
    for (const file of Array.from(files)) {
      const id = crypto.randomUUID();
      setTransfers((items) => [
        ...items,
        { id, name: file.name, progress: 0, status: "Transferindo" },
      ]);
      emit({ type: "DOCUMENT_UPLOAD_STARTED", id });
      await new Promise<void>((resolve) => {
        const xhr = new XMLHttpRequest();
        requests.current.set(id, xhr);
        xhr.open("POST", "/api/knowledge");
        xhr.setRequestHeader("X-Saly-Request", "1");
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable)
            update(id, { progress: Math.round((e.loaded / e.total) * 100) });
        };
        const finish = () => {
          requests.current.delete(id);
          emit({ type: "DOCUMENT_UPLOAD_COMPLETED", id });
          resolve();
          void refresh();
        };
        xhr.onload = () => {
          try {
            const data = JSON.parse(xhr.responseText);
            if (xhr.status >= 400)
              throw Error(
                typeof data.detail === "string"
                  ? data.detail
                  : "Upload recusado",
              );
            update(id, {
              progress: 100,
              status: data.duplicate
                ? "Duplicata já existente"
                : "Recebido — acompanhe o processamento abaixo",
            });
          } catch (e) {
            update(id, { status: "Falha", error: (e as Error).message });
          }
          finish();
        };
        xhr.onerror = () => {
          update(id, { status: "Falha de conexão" });
          finish();
        };
        xhr.onabort = () => {
          update(id, { status: "Transferência cancelada" });
          finish();
        };
        const form = new FormData();
        form.append("file", file);
        xhr.send(form);
      });
    }
  }
  return (
    <>
      <PageTitle
        eyebrow={`CENTRO SMOLIN · ACERVO ${collectionName.toLocaleUpperCase()}`}
        title="Conhecimento com origem."
        text="Seus documentos, páginas e referências em uma base privada. O original e o texto integral permanecem preservados."
      />
      <label
        className="dropzone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          void upload(e.dataTransfer.files);
        }}
      >
        <span>↥</span>
        <strong>Solte seus documentos aqui</strong>
        <small>
          PDF, TXT ou Markdown · múltiplos arquivos · limite padrão de 10 MB por
          arquivo
        </small>
        <input
          type="file"
          multiple
          accept=".pdf,.txt,.md"
          aria-label="Importar documentos"
          onChange={(e) => {
            if (e.target.files) void upload(e.target.files);
            e.target.value = "";
          }}
        />
      </label>
      {transfers.map((t) => (
        <div className="card transfer" key={t.id}>
          <strong>{t.name}</strong>
          <progress
            max="100"
            value={t.progress}
            aria-label={`Transferência de ${t.name}`}
          />
          <small>
            {t.status} · {t.progress}% transferido {t.error}
          </small>
          {requests.current.has(t.id) && (
            <button onClick={() => requests.current.get(t.id)?.abort()}>
              Cancelar transferência
            </button>
          )}
        </div>
      ))}
      <div className="library-stats">
        <span>{docs.length} documentos</span>
        <span>{docs.reduce((a, d) => a + (d.page_count || 0), 0)} páginas</span>
        <span>
          {docs.reduce((a, d) => a + d.file_size, 0).toLocaleString("pt-BR")}{" "}
          bytes preservados
        </span>
        <span>{docs.reduce((a, d) => a + d.chunks, 0)} trechos</span>
      </div>
      <form
        className="toolbar"
        onSubmit={async (e) => {
          e.preventDefault();
          emit({ type: "TOOL_STARTED", id: "search" });
          try {
            setResults(
              await api("/knowledge/search?q=" + encodeURIComponent(query)),
            );
          } catch (e) {
            notify((e as Error).message);
          } finally {
            emit({ type: "TOOL_COMPLETED", id: "search" });
          }
        }}
      >
        <input
          value={query}
          aria-label="Pesquisar Centro Smolin"
          onChange={(e) => setQuery(e.target.value)}
          required
          placeholder="Pesquisar no acervo…"
        />
        <button>Pesquisar</button>
      </form>
      {results.map((r) => (
        <article className="card" key={r.chunk_id}>
          <a href={r.url} target="_blank" rel="noreferrer">
            {r.name} ·{" "}
            {r.page ? `página ${r.page}` : "página não disponível no legado"} ·
            trecho {r.position + 1} ↗
          </a>
          <p>{r.content}</p>
          <small>Referência: {r.chunk_id}</small>
        </article>
      ))}
      {jobs
        .filter((j) => ["processing", "queued"].includes(j.status))
        .map((j) => (
          <div className="card" key={j.id}>
            <small>
              Processamento real ·{" "}
              {docs.find((d) => d.id === j.document_id)?.name} ·{" "}
              {j.processed_pages || 0} páginas extraídas
            </small>
            <progress max="100" value={j.progress} />
            <button
              className="secondary"
              onClick={async () => {
                await post(`/knowledge/jobs/${j.id}/cancel`);
                await refresh();
              }}
            >
              Cancelar processamento
            </button>
          </div>
        ))}
      <div className="memory-grid">
        {docs.map((d) => (
          <article className="card" key={d.id}>
            <div className="memory-meta">
              <span>{d.mime}</span>
              <span>{d.status}</span>
            </div>
            <h2>{d.name}</h2>
            <small>
              {d.page_count ?? "—"} páginas · {d.chunks} trechos · vetores:{" "}
              {d.embedding_status}
            </small>
            <div className="toolbar">
              <button
                className="secondary"
                onClick={async () => setDetail(await api("/knowledge/" + d.id))}
              >
                Detalhes e texto
              </button>
              <a
                className="file-button"
                href={`/api/knowledge/${d.id}/original`}
                target="_blank"
                rel="noreferrer"
              >
                Abrir original ↗
              </a>
              <button
                className="text-button"
                onClick={async () => {
                  try {
                    await post(`/knowledge/${d.id}/reprocess`);
                    await refresh();
                  } catch (e) {
                    notify((e as Error).message);
                  }
                }}
              >
                Reprocessar
              </button>
              <button
                className="danger"
                onClick={async () => {
                  if (
                    !confirm(
                      "Excluir original, páginas, trechos, vetores e referências derivadas? Backups antigos não serão alterados.",
                    )
                  )
                    return;
                  try {
                    await api(`/knowledge/${d.id}?confirm=true`, {
                      method: "DELETE",
                    });
                    setResults([]);
                    setDetail(null);
                    await refresh();
                  } catch (e) {
                    notify((e as Error).message);
                  }
                }}
              >
                Excluir
              </button>
            </div>
            {d.status === "ocr_required" && (
              <p>
                Original preservado. OCR é necessário; nenhum texto foi
                reconhecido.
              </p>
            )}
            {d.status === "partial" && (
              <p>
                Há páginas sem texto. Extração parcial; consulte os detalhes.
              </p>
            )}
          </article>
        ))}
      </div>
      {!docs.length && (
        <Empty text="Nenhum documento ainda. Importe um arquivo para começar seu acervo." />
      )}
      {detail && (
        <section className="card">
          <div className="toolbar">
            <h2>{detail.title || detail.name}</h2>
            <button onClick={() => setDetail(null)}>Fechar detalhes</button>
          </div>
          <p>
            Autor: {detail.author || "não informado"} · SHA-256: {detail.sha256}
          </p>
          <p>
            Pipeline: {detail.pipeline} · Páginas sem texto:{" "}
            {detail.empty_pages?.join(", ") || "nenhuma identificada"}
          </p>
          {!detail.pages.length && detail.content && (
            <pre className="document-text">{detail.content}</pre>
          )}
          {detail.pages.map((p: any) => (
            <details key={p.page}>
              <summary>
                Página {p.page} · {p.content.length} caracteres
              </summary>
              <pre className="document-text">
                {p.content || "OCR necessário."}
              </pre>
            </details>
          ))}
        </section>
      )}
    </>
  );
}
