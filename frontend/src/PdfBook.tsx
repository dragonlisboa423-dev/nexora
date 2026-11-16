import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  getDocument,
  GlobalWorkerOptions,
  TextLayer,
  type PDFDocumentProxy,
  type RenderTask,
} from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { api, put } from "./api";
GlobalWorkerOptions.workerSrc = workerUrl;
function OriginalPage({
  pdf,
  number,
  width,
  zoom,
  rotation,
}: {
  pdf: PDFDocumentProxy;
  number: number;
  width: number;
  zoom: number;
  rotation: number;
}) {
  const canvas = useRef<HTMLCanvasElement>(null),
    text = useRef<HTMLDivElement>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(true);
  useEffect(() => {
    let disposed = false,
      task: RenderTask | undefined,
      layer: TextLayer | undefined;
    setBusy(true);
    setError("");
    (async () => {
      try {
        const page = await pdf.getPage(number);
        if (disposed) return;
        const base = page.getViewport({ scale: 1, rotation });
        const scale = Math.min(2, Math.max(0.1, width / base.width)) * zoom;
        const viewport = page.getViewport({ scale, rotation });
        const surface = canvas.current!,
          container = text.current!;
        const ratio = Math.min(devicePixelRatio || 1, 2);
        surface.width = Math.min(4096, Math.floor(viewport.width * ratio));
        surface.height = Math.min(4096, Math.floor(viewport.height * ratio));
        surface.style.width = `${viewport.width}px`;
        surface.style.height = `${viewport.height}px`;
        container.style.width = `${viewport.width}px`;
        container.style.height = `${viewport.height}px`;
        container.style.setProperty("--scale-factor", String(scale));
        container.style.setProperty("--total-scale-factor", String(scale));
        container.replaceChildren();
        task = page.render({
          canvas: surface,
          viewport,
          transform: [
            surface.width / viewport.width,
            0,
            0,
            surface.height / viewport.height,
            0,
            0,
          ],
        });
        await task.promise;
        if (disposed) return;
        layer = new TextLayer({
          textContentSource: await page.getTextContent(),
          container,
          viewport,
        });
        await layer.render();
        if (!disposed) setBusy(false);
      } catch (error) {
        if (
          !disposed &&
          (error as Error).name !== "RenderingCancelledException"
        ) {
          setError(
            "Não foi possível renderizar esta página. Tente reduzir o zoom ou baixar o original.",
          );
          setBusy(false);
        }
      }
    })();
    return () => {
      disposed = true;
      task?.cancel();
      layer?.cancel();
    };
  }, [pdf, number, width, zoom, rotation]);
  return (
    <article className="pdf-leaf" aria-label={`Página original ${number}`}>
      <div className="pdf-page-art" style={{ minHeight: 160 }}>
        <canvas
          ref={canvas}
          aria-label={`Imagem original da página ${number}`}
        />
        <div ref={text} className="textLayer" />
      </div>
      <small>Página {number}</small>
      {busy && <p role="status">Renderizando página {number}…</p>}
      {error && <p role="alert">{error}</p>}
    </article>
  );
}
export default function PdfBook() {
  const { documentId = "" } = useParams(),
    [params, setParams] = useSearchParams(),
    [loaded, setLoaded] = useState<{
      id: string;
      pdf: PDFDocumentProxy;
    } | null>(null),
    [name, setName] = useState("PDF"),
    [page, setPage] = useState(1),
    [zoom, setZoom] = useState(1),
    [rotation, setRotation] = useState(0),
    [vertical, setVertical] = useState(false),
    [single, setSingle] = useState(matchMedia("(max-width:950px)").matches),
    [width, setWidth] = useState(700),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [outline, setOutline] = useState<{ title: string; page: number }[]>([]),
    [accessible, setAccessible] = useState("");
  const positionQueue = useRef(Promise.resolve());
  const frame = useRef<HTMLDivElement>(null),
    pdf = loaded?.id === documentId ? loaded.pdf : null,
    spread = single ? 1 : 2;
  useEffect(() => {
    const media = matchMedia("(max-width:950px)"),
      change = () => setSingle(media.matches);
    media.addEventListener("change", change);
    return () => media.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    const node = frame.current;
    if (!node) return;
    const observer = new ResizeObserver((entries) =>
      setWidth(Math.max(150, entries[0].contentRect.width)),
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [loading]);
  useEffect(() => {
    let disposed = false;
    setLoading(true);
    setError("");
    setLoaded(null);
    setOutline([]);
    const task = getDocument({
      url: `/api/knowledge/${documentId}/original`,
      enableXfa: false,
      cMapUrl: "/pdfjs/cmaps/",
      cMapPacked: true,
      standardFontDataUrl: "/pdfjs/standard_fonts/",
      wasmUrl: "/pdfjs/wasm/",
      stopAtErrors: false,
    });
    task.onPassword = () => {
      if (!disposed) {
        setError(
          "PDF protegido por senha. Baixe o original e abra em um leitor que permita desbloqueá-lo.",
        );
        setLoading(false);
      }
      void task.destroy();
    };
    (async () => {
      try {
        const [doc, position, document] = await Promise.all([
          api("/knowledge/" + documentId),
          api("/knowledge/" + documentId + "/reading-position"),
          task.promise,
        ]);
        if (disposed) return;
        setName(doc.name);
        const requested = Number(params.get("page") ?? position.page);
        setPage(
          Math.min(
            document.numPages,
            Math.max(1, Number.isInteger(requested) ? requested : 1),
          ),
        );
        setLoaded({ id: documentId, pdf: document });
        setLoading(false);
        const tree = await document.getOutline();
        const items: { title: string; page: number }[] = [];
        async function visit(nodes: any[], depth = 0) {
          for (const node of nodes) {
            if (items.length >= 100 || depth > 4) return;
            try {
              const destination =
                typeof node.dest === "string"
                  ? await document.getDestination(node.dest)
                  : node.dest;
              if (destination) {
                const position =
                  typeof destination[0] === "number"
                    ? destination[0]
                    : await document.getPageIndex(destination[0]);
                items.push({ title: node.title, page: position + 1 });
              }
            } catch {}
            if (node.items?.length) await visit(node.items, depth + 1);
          }
        }
        await visit(tree ?? []);
        if (!disposed) setOutline(items);
      } catch {
        if (!disposed) {
          setError(
            "Não foi possível abrir o PDF original. Confira sua sessão, o arquivo ou use Baixar original.",
          );
          setLoading(false);
        }
      }
    })();
    return () => {
      disposed = true;
      void task.destroy();
    };
  }, [documentId]);
  function turn(value: number) {
    if (!pdf) return;
    const next = Math.max(1, Math.min(pdf.numPages, value));
    setPage(next);
    const key = documentId;
    positionQueue.current = positionQueue.current
      .catch(() => {})
      .then(() => put(`/knowledge/${key}/reading-position`, { page: next }))
      .then(() => {})
      .catch(() =>
        setError(
          "A página foi aberta, mas não foi possível guardar a posição. Confira sua sessão.",
        ),
      );
    setAccessible("");
    setParams({ page: String(next) }, { replace: true });
  }
  async function readText() {
    if (!pdf) return;
    try {
      const content = await (await pdf.getPage(page)).getTextContent();
      setAccessible(
        content.items
          .map((item) => ("str" in item ? item.str : ""))
          .join(" ") ||
          "Esta página não contém camada de texto. O original visual continua preservado; OCR pode ser necessário.",
      );
    } catch {
      setError("Não foi possível ler a camada de texto desta página.");
    }
  }
  const pages = pdf
    ? Array.from(
        { length: Math.min(spread, pdf.numPages - page + 1) },
        (_, i) => page + i,
      )
    : [];
  return (
    <section className="pdf-book">
      <Link to="/knowledge">← Voltar ao Centro Smolin</Link>
      <h1>{name}</h1>
      <p>
        Páginas renderizadas do arquivo original, com imagens e diagramação
        preservadas. Não é uma reconstrução a partir do texto extraído.
      </p>
      <div className="toolbar">
        <a
          className="file-button"
          href={`/api/knowledge/${documentId}/original?download=true`}
          download
        >
          Baixar PDF original
        </a>
        <a
          className="file-button"
          href={`/api/knowledge/${documentId}/original`}
          target="_blank"
          rel="noopener noreferrer"
        >
          Abrir no leitor do navegador
        </a>
        <label>
          Zoom do PDF
          <input
            aria-label="Zoom do PDF"
            type="range"
            min=".5"
            max="2"
            step=".1"
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
          />
          {Math.round(zoom * 100)}%
        </label>
        <button onClick={() => setRotation((rotation + 90) % 360)}>
          Girar páginas
        </button>
        <label>
          <input
            type="checkbox"
            checked={vertical}
            onChange={(e) => setVertical(e.target.checked)}
          />
          Desativar animação de virada
        </label>
        <label>
          <input
            type="checkbox"
            checked={single}
            onChange={(e) => setSingle(e.target.checked)}
          />
          Uma página por vez
        </label>
      </div>
      {loading && <p role="status">Abrindo o PDF original…</p>}
      {error && <p role="alert">{error}</p>}
      {pdf && (
        <>
          <div className="toolbar">
            <button disabled={page <= 1} onClick={() => turn(page - spread)}>
              Página anterior do PDF
            </button>
            <label>
              Ir para a página
              <input
                aria-label="Ir para a página do PDF"
                type="number"
                min="1"
                max={pdf.numPages}
                value={page}
                onChange={(e) => {
                  const next = Number(e.target.value);
                  if (
                    Number.isInteger(next) &&
                    next >= 1 &&
                    next <= pdf.numPages
                  )
                    turn(next);
                }}
              />
            </label>
            <strong role="status">
              Página {page} de {pdf.numPages}
            </strong>
            <button
              disabled={page + spread > pdf.numPages}
              onClick={() => turn(page + spread)}
            >
              Próxima página do PDF
            </button>
          </div>
          {outline.length > 0 && (
            <details>
              <summary>Sumário original do PDF</summary>
              {outline.map((item, index) => (
                <button key={index} onClick={() => turn(item.page)}>
                  {item.title} · {item.page}
                </button>
              ))}
            </details>
          )}
          <progress
            aria-label="Posição no PDF"
            max={pdf.numPages}
            value={page}
          />
        </>
      )}
      <div
        ref={frame}
        className={`pdf-book-frame ${vertical ? "no-turn" : ""}`}
        tabIndex={0}
        aria-label="Livro PDF original"
        onKeyDown={(e) => {
          if (e.target !== e.currentTarget) return;
          if (e.key === "ArrowRight") {
            e.preventDefault();
            turn(page + spread);
          }
          if (e.key === "ArrowLeft") {
            e.preventDefault();
            turn(page - spread);
          }
        }}
      >
        <div
          className="pdf-original-spread"
          key={`${page}-${spread}`}
          style={{
            gridTemplateColumns: `repeat(${single ? 1 : 2},max-content)`,
          }}
        >
          {pdf &&
            pages.map((number) => (
              <OriginalPage
                key={number}
                pdf={pdf}
                number={number}
                width={(width - (single ? 0 : 18)) / (single ? 1 : 2) - 20}
                zoom={zoom}
                rotation={rotation}
              />
            ))}
        </div>
      </div>
      {pdf && (
        <>
          <button onClick={() => void readText()}>
            Mostrar texto acessível da página atual
          </button>
          {accessible && (
            <div
              className="card pdf-accessible"
              role="region"
              aria-label="Texto da página original"
            >
              {accessible}
            </div>
          )}
        </>
      )}
      <p>
        Atalhos: foque o livro e use ← / →. Zoom e seleção de texto não viram
        páginas. A posição fica guardada no servidor; este leitor precisa de
        conexão para buscar o original.
      </p>
    </section>
  );
}
