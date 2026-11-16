import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { smolinError, uploadResponse } from "./smolin_transfer";
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
    [detail, setDetail] = useState<any>(null),
    [capabilities, setCapabilities] = useState<any>(null);
  const requests = useRef(new Map<string, XMLHttpRequest>()),
    active = useRef(new Set<string>()),
    cancelled = useRef(new Set<string>());
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
      notify(
        e instanceof SyntaxError
          ? "Resposta inesperada do servidor/proxy. Confira sua sessão da SALY e tente novamente."
          : (e as Error).message,
      );
    }
  };
  useEffect(() => {
    void refresh();
    api("/knowledge/capabilities")
      .then(setCapabilities)
      .catch((error) => notify(error.message));
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
  function request(
    id: string,
    method: string,
    url: string,
    body: Document | XMLHttpRequestBodyInit | null,
    base = 0,
    total = 0,
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      if (cancelled.current.has(id)) {
        reject(new Error("Transferência cancelada."));
        return;
      }
      const xhr = new XMLHttpRequest();
      requests.current.set(id, xhr);
      xhr.open(method, url);
      xhr.timeout = 120000;
      xhr.setRequestHeader("X-Saly-Request", "1");
      if (body instanceof Blob)
        xhr.setRequestHeader("Content-Type", "application/octet-stream");
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable)
          update(id, {
            progress: Math.min(
              99,
              Math.round(
                total
                  ? ((base + event.loaded) / total) * 100
                  : (event.loaded / event.total) * 100,
              ),
            ),
          });
      };
      const finish = () => requests.current.delete(id);
      xhr.onload = () => {
        finish();
        try {
          resolve(
            uploadResponse(
              xhr.responseText,
              xhr.status,
              xhr.getResponseHeader("Content-Type") ?? "",
            ),
          );
        } catch (e) {
          reject(e);
        }
      };
      xhr.onerror = () => {
        finish();
        reject(
          new Error("Falha de conexão; verifique o acervo antes de repetir."),
        );
      };
      xhr.ontimeout = () => {
        finish();
        reject(
          new Error(
            "Tempo limite no envio. Confira sua conexão e tente novamente.",
          ),
        );
      };
      xhr.onabort = () => {
        finish();
        reject(
          new Error(
            "Transferência cancelada; confira se o arquivo já apareceu no acervo.",
          ),
        );
      };
      xhr.send(body);
    });
  }
  async function upload(files: FileList | File[]) {
    for (const file of Array.from(files)) {
      const id = crypto.randomUUID();
      let session: string | undefined;
      setTransfers((items) => [
        ...items,
        { id, name: file.name, progress: 0, status: "Transferindo" },
      ]);
      emit({ type: "DOCUMENT_UPLOAD_STARTED", id });
      try {
        if (capabilities && file.size > capabilities.max_upload_bytes)
          throw new Error(
            `Arquivo acima do limite atual de ${Math.round(capabilities.max_upload_bytes / 1024 / 1024)} MB.`,
          );
        let result: any;
        if (file.size > 4 * 1024 * 1024) {
          const initialized = await post("/knowledge/uploads", {
            name: file.name,
            size: file.size,
          });
          session = initialized.id;
          for (let offset = 0; offset < file.size;) {
            const end = Math.min(file.size, offset + initialized.chunk_bytes);
            const acknowledged = await request(
              id,
              "PUT",
              `/api/knowledge/uploads/${session}?offset=${offset}`,
              file.slice(offset, end),
              offset,
              file.size,
            );
            offset = acknowledged.offset;
          }
          if (cancelled.current.has(id))
            throw new Error("Transferência cancelada.");
          result = await post(`/knowledge/uploads/${session}/complete`);
          session = undefined;
        } else {
          const form = new FormData();
          form.append("file", file);
          result = await request(id, "POST", "/api/knowledge", form);
        }
        if (typeof result.id !== "string")
          throw new Error("Servidor não confirmou o arquivo.");
        update(id, {
          progress: 100,
          status: result.duplicate
            ? "Arquivo já existente"
            : result.status === "stored_only"
              ? "Original guardado; formato sem interpretação"
              : "Original guardado — acompanhe a interpretação",
        });
      } catch (error) {
        update(id, {
          status: cancelled.current.has(id) ? "Cancelada" : "Falha",
          error: smolinError(error),
        });
      } finally {
        if (session)
          await api(`/knowledge/uploads/${session}`, {
            method: "DELETE",
          }).catch(() => {});
        requests.current.delete(id);
        cancelled.current.delete(id);
        emit({ type: "DOCUMENT_UPLOAD_COMPLETED", id });
        void refresh();
      }
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
          Todos os formatos podem ser guardados e baixados · até{" "}
          {Math.round(
            (capabilities?.max_upload_bytes ?? 64 * 1024 * 1024) / 1024 / 1024,
          )}{" "}
          MB por arquivo · envios grandes em blocos de 2 MB
        </small>
        <input
          type="file"
          multiple
          aria-label="Importar documentos"
          onChange={(e) => {
            if (e.target.files) void upload(e.target.files);
            e.target.value = "";
          }}
        />
      </label>
      <p>
        PDF, textos e arquivos Office/EPUB têm extração local. Imagens usam OCR
        quando instalado; vídeos usam quadros amostrados. Outros formatos ficam
        guardados sem execução nem alegação de interpretação.
      </p>
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
            <button
              onClick={() => {
                cancelled.current.add(t.id);
                requests.current.get(t.id)?.abort();
              }}
            >
              Cancelar transferência
            </button>
          )}
        </div>
      ))}
      <div className="library-stats">
        <span>{docs.length} documentos</span>
        <span>
          {docs
            .filter((d) => d.mime === "application/pdf")
            .reduce((a, d) => a + (d.page_count || 0), 0)}{" "}
          páginas PDF
        </span>
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
            notify(
              e instanceof SyntaxError
                ? "Resposta inesperada do servidor/proxy. Confira sua sessão da SALY e tente novamente."
                : (e as Error).message,
            );
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
              {j.processed_pages || 0} partes indexadas
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
              {d.page_count ?? "—"}{" "}
              {d.unit === "page" || !d.unit
                ? "páginas"
                : "seções/quadros/segmentos"}{" "}
              · {d.chunks} trechos · vetores: {d.embedding_status}
            </small>
            <div className="toolbar">
              <button
                className="secondary"
                onClick={async () => {
                  try {
                    setDetail(await api("/knowledge/" + d.id));
                  } catch (error) {
                    notify(
                      error instanceof SyntaxError
                        ? "Servidor/proxy respondeu em formato inesperado. Confira sua sessão."
                        : (error as Error).message,
                    );
                  }
                }}
              >
                Detalhes e texto
              </button>
              {d.mime === "application/pdf" && (
                <Link className="file-button" to={`/knowledge/${d.id}/read`}>
                  Ler PDF como livro
                </Link>
              )}
              <a
                className="file-button"
                href={`/api/knowledge/${d.id}/original?download=true`}
                download={d.name}
              >
                Baixar original
              </a>
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
                disabled={d.kind === "binary"}
                onClick={async () => {
                  try {
                    await post(`/knowledge/${d.id}/reprocess`);
                    await refresh();
                  } catch (e) {
                    notify(
                      e instanceof SyntaxError
                        ? "Resposta inesperada do servidor/proxy. Confira sua sessão da SALY e tente novamente."
                        : (e as Error).message,
                    );
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
                    notify(
                      e instanceof SyntaxError
                        ? "Resposta inesperada do servidor/proxy. Confira sua sessão da SALY e tente novamente."
                        : (e as Error).message,
                    );
                  }
                }}
              >
                Excluir
              </button>
            </div>
            {d.interpretation_notice && <p>{d.interpretation_notice}</p>}
            {d.media_info && (
              <p>
                Duração: {d.media_info.duration_seconds?.toFixed(1)} s ·{" "}
                {d.transcribed
                  ? "Fala transcrita automaticamente; revise erros."
                  : "Fala ainda não transcrita."}
              </p>
            )}
            {d.kind === "audio" && (
              <audio
                controls
                preload="none"
                src={`/api/knowledge/${d.id}/original`}
              />
            )}
            {d.kind === "video" && (
              <video
                className="smolin-video"
                controls
                preload="none"
                src={`/api/knowledge/${d.id}/original`}
              />
            )}
            {["audio", "video"].includes(d.kind) && (
              <button
                className="secondary"
                disabled={!capabilities?.transcription.available}
                onClick={async () => {
                  try {
                    await post(`/knowledge/${d.id}/transcribe`);
                    await refresh();
                  } catch (error) {
                    notify((error as Error).message);
                  }
                }}
              >
                Transcrever fala localmente
              </button>
            )}
            {["audio", "video"].includes(d.kind) &&
              !capabilities?.transcription.available && (
                <p>
                  Transcrição local não instalada (até 30 minutos por arquivo).
                  No servidor:{" "}
                  <code>bash scripts/install-transcription.sh</code>. Metadados
                  e OCR de quadros não substituem a transcrição.
                </p>
              )}
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
          {!detail.pages?.length && detail.content && (
            <pre className="document-text">{detail.content}</pre>
          )}
          {detail.pages?.map((p: any) => (
            <details key={p.page}>
              <summary>
                {p.label ??
                  (detail.unit === "page" || !detail.unit
                    ? `Página ${p.page}`
                    : `Trecho ${p.page}`)}{" "}
                {p.start_seconds !== undefined
                  ? ` · ${p.start_seconds.toFixed(2)}s`
                  : ""}{" "}
                · {p.content.length} caracteres
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
