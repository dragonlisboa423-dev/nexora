import { api, ApiError, post, put } from "../api";
import type { BookDocument } from "../Library";
import { base64ToBytes, bytesToBase64, type VaultState } from "./vault";
type Data = Record<string, any>;
export type OfflineBook = {
  book: BookDocument;
  progress: Data;
  annotations: Data[];
  assets: Record<string, { mime: string; base64: string; sha256: string }>;
  pendingNotes: Data[];
  dirty: boolean;
  copiedAt: string;
  remoteConflict?: Data;
};
export function progressFields(p: Data) {
  return {
    current_page_id: p.current_page_id ?? null,
    completed_pages: p.completed_pages ?? [],
    bookmarks: p.bookmarks ?? [],
    quiz_attempts: p.quiz_attempts ?? {},
  };
}
function sameProgress(a: Data, b: Data) {
  return (
    JSON.stringify(progressFields(a)) === JSON.stringify(progressFields(b))
  );
}
export async function copyBook(
  id: string,
  edition: string,
  media: boolean,
): Promise<OfflineBook> {
  const [book, progress, annotations, assets] = await Promise.all([
    api(`/books/${id}?edition_name=${edition}`),
    api(`/books/${id}/progress`),
    api(`/books/${id}/annotations`),
    media ? api(`/books/${id}/assets`) : Promise.resolve([]),
  ]);
  const references = new Set<string>(
    book.cover_asset_id ? [book.cover_asset_id] : [],
  );
  for (const chapter of book.chapters)
    for (const page of chapter.pages)
      for (const block of page.blocks)
        if (block.asset_id) references.add(block.asset_id);
  const files: OfflineBook["assets"] = {};
  for (const asset of assets.filter((a: Data) => references.has(a.id))) {
    if (asset.size > 5 * 1024 * 1024)
      throw new Error(
        "Mídia acima de 5 MB; baixe sem mídias ou reduza o arquivo no livro.",
      );
    const response = await fetch("/api/private-assets/" + asset.id);
    if (!response.ok) throw new Error("Mídia privada indisponível.");
    const bytes = new Uint8Array(await response.arrayBuffer());
    if (bytes.length > 5 * 1024 * 1024)
      throw new Error("Mídia acima do limite local.");
    const digest = Array.from(
      new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
      (b) => b.toString(16).padStart(2, "0"),
    ).join("");
    if (digest !== asset.sha256)
      throw new Error(
        "Integridade da mídia mudou. Tente baixar a edição novamente.",
      );
    files[asset.id] = {
      mime: asset.mime,
      base64: bytesToBase64(bytes),
      sha256: digest,
    };
  }
  return {
    book,
    progress,
    annotations,
    assets: files,
    pendingNotes: [],
    dirty: false,
    copiedAt: new Date().toISOString(),
  };
}
export function validateBooks(books: VaultState["books"]) {
  if (books === undefined) return;
  if (!books || typeof books !== "object" || Object.keys(books).length > 20)
    throw new Error("Biblioteca local incompatível.");
  for (const snapshot of Object.values(books)) {
    if (
      !snapshot.book?.id ||
      !Array.isArray(snapshot.book.chapters) ||
      !Array.isArray(snapshot.progress?.bookmarks) ||
      !Array.isArray(snapshot.progress?.completed_pages) ||
      !Array.isArray(snapshot.annotations) ||
      !Array.isArray(snapshot.pendingNotes) ||
      !snapshot.assets
    )
      throw new Error("Livro local inválido.");
    for (const chapter of snapshot.book.chapters) {
      if (!Array.isArray(chapter.pages)) throw new Error("Capítulo inválido.");
      for (const page of chapter.pages) {
        if (
          typeof page.id !== "string" ||
          typeof page.title !== "string" ||
          !Array.isArray(page.blocks) ||
          !Array.isArray(page.sources)
        )
          throw new Error("Página local inválida.");
        for (const block of page.blocks) {
          if (
            ![
              "text",
              "image",
              "audio",
              "video",
              "quiz",
              "cellViewer",
              "dnaLab",
              "ecologyLab",
              "microscope",
            ].includes(block.type)
          )
            throw new Error("Bloco local incompatível.");
          if (block.type === "text" && typeof block.text !== "string")
            throw new Error("Texto local inválido.");
          if (
            block.type === "quiz" &&
            (!Array.isArray(block.choices) ||
              typeof block.explanation !== "string")
          )
            throw new Error("Quiz inválido.");
        }
      }
    }
    for (const asset of Object.values(snapshot.assets)) {
      if (
        !["image/png", "audio/wav", "video/mp4"].includes(asset.mime) ||
        typeof asset.base64 !== "string" ||
        base64ToBytes(asset.base64).length > 5 * 1024 * 1024
      )
        throw new Error("Mídia local inválida.");
    }
  }
}
export async function synchronizeBooks(
  state: VaultState,
  persist: (s: VaultState) => Promise<VaultState>,
): Promise<VaultState> {
  let next = structuredClone(state);
  for (const id of Object.keys(next.books ?? {})) {
    const local = next.books![id];
    if (local.remoteConflict) continue;
    try {
      await api(`/books/${id}?edition_name=${local.book.edition ?? "draft"}`);
      const remote = await api(`/books/${id}/progress`);
      if (local.dirty) {
        if (
          remote.revision !== local.progress.revision &&
          !sameProgress(remote, local.progress)
        )
          local.remoteConflict = {
            progress: remote,
            detail:
              "Progresso mudou em outro dispositivo; revise antes de enviar.",
          };
        else {
          local.progress = sameProgress(remote, local.progress)
            ? remote
            : await put(`/books/${id}/progress`, {
                ...progressFields(local.progress),
                base_revision: remote.revision,
              });
          local.dirty = false;
        }
      }
      if (!local.dirty && !local.remoteConflict)
        local.progress =
          remote.revision >= local.progress.revision ? remote : local.progress;
      if (!local.remoteConflict) {
        local.annotations = await api(`/books/${id}/annotations`);
        for (const pending of [...local.pendingNotes]) {
          const note = await post(`/books/${id}/annotations`, {
            page_id: pending.page_id,
            note: pending.note,
            selected_text: "",
            confirm: true,
            client_operation_id: pending.client_operation_id,
          });
          local.pendingNotes = local.pendingNotes.filter(
            (n) => n.client_operation_id !== pending.client_operation_id,
          );
          if (!local.annotations.some((n) => n.id === note.id))
            local.annotations.push(note);
          next = await persist(next);
        }
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        if (local.dirty || local.pendingNotes.length)
          local.remoteConflict = {
            deleted: true,
            detail:
              "Livro/edição foi excluído ou retirado. Exporte os rascunhos; o livro não será recriado automaticamente.",
          };
        else delete next.books![id];
      } else if (error instanceof ApiError && error.status === 409) {
        local.remoteConflict = {
          progress: await api(`/books/${id}/progress`),
          detail:
            "Progresso alterado durante a sincronização. Revise as versões.",
        };
      } else if (error instanceof ApiError && error.status === 422) {
        local.remoteConflict = {
          invalid: true,
          detail:
            "A página ou configuração mudou no servidor. Exporte o rascunho e baixe uma edição atual.",
        };
      } else throw error;
    }
    next = await persist(next);
  }
  return next;
}
