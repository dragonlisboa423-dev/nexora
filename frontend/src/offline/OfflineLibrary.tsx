import { useEffect, useState } from "react";
import { api, download } from "../api";
import { BookBlocks } from "../Library";
import { ScienceBlock } from "../Science";
import { base64ToBytes, type VaultState } from "./vault";
import { copyBook, type OfflineBook } from "./books";
type Data = Record<string, any>;
export default function OfflineLibrary({
  state,
  save,
  exclusive,
  busy,
  online,
  fail,
}: {
  state: VaultState;
  save: (s: VaultState) => Promise<void>;
  exclusive: (op: (s: VaultState) => Promise<VaultState>) => Promise<void>;
  busy: boolean;
  online: boolean;
  fail: (s: string) => void;
}) {
  const [catalog, setCatalog] = useState<Data[]>([]),
    [selected, setSelected] = useState(""),
    [includeMedia, setIncludeMedia] = useState(false),
    [edition, setEdition] = useState("draft"),
    [note, setNote] = useState(""),
    [urls, setUrls] = useState<Record<string, string>>({});
  const books = state.books ?? {},
    snapshot = books[selected],
    pages =
      snapshot?.book.chapters.flatMap((c) =>
        c.pages.map((p) => ({ ...p, chapterTitle: c.title })),
      ) ?? [],
    index = Math.max(
      0,
      pages.findIndex((p) => p.id === snapshot?.progress.current_page_id),
    ),
    page = pages[index];
  const assetSignature = Object.entries(snapshot?.assets ?? {})
    .map(([id, a]) => id + a.sha256)
    .join("|");
  useEffect(() => {
    const mapping: Record<string, string> = {};
    if (snapshot)
      for (const [id, file] of Object.entries(snapshot.assets))
        mapping[id] = URL.createObjectURL(
          new Blob([base64ToBytes(file.base64) as BlobPart], {
            type: file.mime,
          }),
        );
    setUrls(mapping);
    return () => {
      Object.values(mapping).forEach(URL.revokeObjectURL);
    };
  }, [selected, assetSignature]);
  function update(change: (book: OfflineBook) => void) {
    const next = structuredClone(state);
    const local = next.books?.[selected];
    if (local) {
      change(local);
      void save(next);
    }
  }
  const localAsk = () =>
    fail(
      "Tutoria remota precisa de internet. Abra a edição online e prepare a pergunta; nenhum modelo local foi instalado.",
    );
  return (
    <section>
      <h2>Livros guardados</h2>
      <p>
        Baixe uma edição com consentimento. Textos, atividades e mídias
        escolhidas ficam criptografados. Progresso e novas notas entram na
        sincronização ao reconectar; autoria de livros continua online.
      </p>
      <div className="toolbar">
        <button
          disabled={busy || !online}
          onClick={() =>
            api("/books")
              .then(setCatalog)
              .catch((e) => fail(e.message))
          }
        >
          Consultar livros para baixar
        </button>
        <label>
          Edição a guardar
          <select
            aria-label="Edição a guardar"
            value={edition}
            onChange={(e) => setEdition(e.target.value)}
          >
            <option value="draft">Rascunho</option>
            <option value="published">Publicada</option>
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            checked={includeMedia}
            onChange={(e) => setIncludeMedia(e.target.checked)}
          />
          Incluir mídias privadas até 5 MB cada
        </label>
      </div>
      {catalog.map((book) => (
        <p key={book.id}>
          {book.title}
          <button
            disabled={
              busy ||
              !online ||
              Boolean(
                books[book.id]?.dirty || books[book.id]?.pendingNotes.length,
              )
            }
            onClick={async () => {
              if (
                !confirm(
                  "Guardar/substituir cópia criptografada desta edição e das mídias selecionadas no dispositivo?",
                )
              )
                return;
              try {
                await exclusive(async (current) => ({
                  ...current,
                  books: {
                    ...current.books,
                    [book.id]: await copyBook(book.id, edition, includeMedia),
                  },
                }));
                setSelected(book.id);
              } catch (e) {
                fail((e as Error).message);
              }
            }}
          >
            Guardar livro {book.title}
          </button>
        </p>
      ))}
      <div className="toolbar">
        <label>
          Livro local
          <select
            aria-label="Livro local"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">Escolha um livro guardado</option>
            {Object.entries(books).map(([id, b]) => (
              <option key={id} value={id}>
                {b.book.title}
              </option>
            ))}
          </select>
        </label>
      </div>
      {!Object.keys(books).length && (
        <p>Nenhum livro guardado neste dispositivo.</p>
      )}
      {snapshot && (
        <>
          <h3>{snapshot.book.title}</h3>
          <p>
            Edição: {snapshot.book.edition} · cópia de {snapshot.copiedAt} ·{" "}
            {snapshot.dirty
              ? "progresso aguardando envio"
              : "progresso sincronizado"}{" "}
            · {snapshot.pendingNotes.length} nota(s) pendente(s).
          </p>
          <div className="toolbar">
            <button onClick={() => download("saly-livro-local.json", snapshot)}>
              Exportar cópia e rascunhos locais
            </button>
            <button
              disabled={busy}
              onClick={() => {
                if (
                  !confirm(
                    "Remover somente a cópia deste dispositivo, inclusive notas ainda não enviadas? Exporte antes se necessário.",
                  )
                )
                  return;
                const next = structuredClone(state);
                delete next.books![selected];
                void save(next);
                setSelected("");
              }}
            >
              Remover livro deste cofre
            </button>
          </div>
          {snapshot.remoteConflict && (
            <section className="card" role="alert">
              <h3>Revisar sincronização do livro</h3>
              <p>{snapshot.remoteConflict.detail}</p>
              <details>
                <summary>Progresso local e do servidor</summary>
                <pre className="tool-result">
                  {JSON.stringify(
                    {
                      local: snapshot.progress,
                      server: snapshot.remoteConflict.progress,
                    },
                    null,
                    2,
                  )}
                </pre>
              </details>
              {snapshot.remoteConflict.progress && (
                <>
                  <button
                    disabled={busy}
                    onClick={() =>
                      update((b) => {
                        b.progress = b.remoteConflict!.progress;
                        b.dirty = false;
                        delete b.remoteConflict;
                      })
                    }
                  >
                    Manter progresso do servidor
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => {
                      if (
                        confirm(
                          "Reenviar progresso local sobre a versão apresentada?",
                        )
                      )
                        update((b) => {
                          b.progress.revision =
                            b.remoteConflict!.progress.revision;
                          b.dirty = true;
                          delete b.remoteConflict;
                        });
                    }}
                  >
                    Reenviar progresso local revisado
                  </button>
                </>
              )}
            </section>
          )}
          <label>
            Sumário local
            <select
              aria-label="Sumário local"
              value={index}
              onChange={(e) =>
                update((b) => {
                  b.progress.current_page_id = pages[Number(e.target.value)].id;
                  b.dirty = true;
                })
              }
            >
              {pages.map((p, i) => (
                <option key={p.id} value={i}>
                  {i + 1}. {p.title}
                </option>
              ))}
            </select>
          </label>
          {page ? (
            <article className="book-leaf">
              <small>
                {page.chapterTitle} · {index + 1}/{pages.length}
              </small>
              <h2>{page.title}</h2>
              <BookBlocks
                page={page}
                version={snapshot.book.version_id ?? "snapshot"}
                attempts={snapshot.progress.quiz_attempts ?? {}}
                answer={(key, answer) =>
                  update((b) => {
                    b.progress.quiz_attempts = {
                      ...b.progress.quiz_attempts,
                      [key]: [
                        ...(b.progress.quiz_attempts?.[key] ?? []),
                        answer,
                      ].slice(-100),
                    };
                    b.dirty = true;
                  })
                }
                assetUrl={(id) => urls[id]}
                science={(block) => (
                  <ScienceBlock block={block} onAsk={localAsk} />
                )}
              />
              <div className="toolbar">
                <button
                  disabled={busy}
                  onClick={() =>
                    update((b) => {
                      b.progress.completed_pages = [
                        ...new Set([...b.progress.completed_pages, page.id]),
                      ];
                      b.dirty = true;
                    })
                  }
                >
                  Concluir página local
                </button>
                <button
                  disabled={busy}
                  onClick={() =>
                    update((b) => {
                      b.progress.bookmarks = b.progress.bookmarks.includes(
                        page.id,
                      )
                        ? b.progress.bookmarks.filter(
                            (id: string) => id !== page.id,
                          )
                        : [...b.progress.bookmarks, page.id];
                      b.dirty = true;
                    })
                  }
                >
                  Alternar marcador local
                </button>
                <button
                  disabled={busy || index === 0}
                  onClick={() =>
                    update((b) => {
                      b.progress.current_page_id = pages[index - 1].id;
                      b.dirty = true;
                    })
                  }
                >
                  Página local anterior
                </button>
                <button
                  disabled={busy || index >= pages.length - 1}
                  onClick={() =>
                    update((b) => {
                      b.progress.current_page_id = pages[index + 1].id;
                      b.dirty = true;
                    })
                  }
                >
                  Próxima página local
                </button>
              </div>
              <p>
                {snapshot.progress.completed_pages.length} página(s)
                concluída(s).
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (
                    !confirm(
                      "Guardar e autorizar sincronização desta nota privada?",
                    )
                  )
                    return;
                  update((b) => {
                    b.pendingNotes.push({
                      client_operation_id: crypto.randomUUID(),
                      page_id: page.id,
                      note,
                    });
                  });
                  setNote("");
                }}
              >
                <label>
                  Anotação local do livro
                  <textarea
                    required
                    maxLength={5000}
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                  />
                </label>
                <button disabled={busy || Boolean(snapshot.remoteConflict)}>
                  Guardar anotação local
                </button>
              </form>
              {[...snapshot.annotations, ...snapshot.pendingNotes]
                .filter((n) => n.page_id === page.id)
                .map((n, i) => (
                  <p key={n.id ?? n.client_operation_id ?? i}>{n.note}</p>
                ))}
            </article>
          ) : (
            <p>Livro sem páginas nesta edição.</p>
          )}
        </>
      )}
    </section>
  );
}
