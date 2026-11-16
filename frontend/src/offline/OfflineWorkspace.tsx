import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import OfflinePlanning, { planningSnapshot } from "./OfflinePlanning";
import OfflineLibrary from "./OfflineLibrary";
import { synchronizeBooks } from "./books";
import PersonalOffline from "./PersonalOffline";
import { Menu, LockKeyhole } from "lucide-react";
import { api, download } from "../api";
import { initialState, queueEdit, resolveConflict, synchronize } from "./sync";
import {
  base64ToBytes,
  bytesToBase64,
  clearVault,
  createVault,
  encryptedBackup,
  restoreBackup,
  saveVault,
  unlockVault,
  vaultExists,
  type RecordData,
  type VaultState,
} from "./vault";

const memoryFields = [
  "content",
  "category",
  "tags",
  "source",
  "verification",
  "archived",
  "enabled",
  "importance",
  "expires_at",
  "relations",
];
const reminderFields = [
  "title",
  "due_at",
  "project",
  "timezone",
  "done",
  "importance",
  "description",
  "priority",
  "calendar_event_id",
  "completed_at",
];
function payload(record: RecordData, fields: string[]) {
  return Object.fromEntries(
    fields
      .filter((field) => field in record)
      .map((field) => [field, record[field]]),
  );
}

function localDateTime(value: string, timezone: string) {
  if (!value || !/(Z|[+-]\d\d:\d\d)$/.test(value)) return value;
  const parts = new Intl.DateTimeFormat("sv-SE", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(value));
  const field = (name: string) =>
    parts.find((part) => part.type === name)?.value ?? "";
  return `${field("year")}-${field("month")}-${field("day")}T${field("hour")}:${field("minute")}`;
}

export default function OfflineWorkspace() {
  const [exists, setExists] = useState<boolean | null>(null),
    [key, setKey] = useState<CryptoKey | null>(null),
    [state, setState] = useState<VaultState | null>(null);
  const [password, setPassword] = useState(""),
    [consent, setConsent] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("memories"),
    [menu, setMenu] = useState(false),
    [online, setOnline] = useState(navigator.onLine),
    [query, setQuery] = useState("");
  const [editing, setEditing] = useState<RecordData | null>(null),
    [restoration, setRestoration] = useState<unknown>(null);
  const stateRef = useRef<VaultState | null>(null),
    active = useRef(false),
    controller = useRef(new AbortController());
  function update(value: VaultState) {
    stateRef.current = value;
    setState(value);
  }
  async function persist(value: VaultState) {
    if (!key) throw new Error("Cofre bloqueado.");
    const saved = await saveVault(key, value);
    update(saved);
    return saved;
  }
  useEffect(() => {
    vaultExists()
      .then(setExists)
      .catch((error) => setError(error.message));
    return () => controller.current.abort();
  }, []);
  async function sync() {
    if (!key || !stateRef.current || active.current || stateRef.current.paused)
      return;
    active.current = true;
    setBusy(true);
    setError("");
    try {
      const synchronized = await synchronize(
        stateRef.current,
        persist,
        controller.current.signal,
      );
      const withBooks = await synchronizeBooks(synchronized, persist);
      if (withBooks.planning)
        await persist({ ...withBooks, planning: await planningSnapshot() });
      setNotice("Sincronização concluída. Confira os conflitos, se houver.");
    } catch (error) {
      if ((error as Error).name !== "AbortError")
        setError((error as Error).message + " A fila local foi preservada.");
    } finally {
      active.current = false;
      setBusy(false);
    }
  }
  useEffect(() => {
    const restored = () => {
        setOnline(true);
        void sync();
      },
      lost = () => setOnline(false);
    window.addEventListener("online", restored);
    window.addEventListener("offline", lost);
    if (key && navigator.onLine) void sync();
    return () => {
      window.removeEventListener("online", restored);
      window.removeEventListener("offline", lost);
    };
  }, [key]);
  function lock() {
    controller.current.abort();
    controller.current = new AbortController();
    setKey(null);
    setState(null);
    stateRef.current = null;
    setPassword("");
    setEditing(null);
    setNotice("");
  }
  async function saveLocal(next: VaultState) {
    if (active.current) return;
    active.current = true;
    setBusy(true);
    setError("");
    try {
      await persist(next);
      setEditing(null);
      setNotice(
        "Alteração salva no cofre. Aguarda sincronização se houver fila.",
      );
    } catch (error) {
      setError((error as Error).message);
    } finally {
      active.current = false;
      setBusy(false);
    }
    if (navigator.onLine && stateRef.current && !stateRef.current.paused)
      void sync();
  }
  async function exclusive(
    operation: (current: VaultState) => Promise<VaultState>,
  ) {
    if (active.current || !stateRef.current)
      throw new Error("Aguarde a operação atual do cofre.");
    active.current = true;
    setBusy(true);
    try {
      await persist(await operation(stateRef.current));
    } finally {
      active.current = false;
      setBusy(false);
    }
  }
  async function enablePersonal() {
    if (active.current || !stateRef.current) return;
    active.current = true;
    setBusy(true);
    try {
      const [snapshot, personal] = await Promise.all([
        api("/sync/bootstrap?kinds=purchases,drawers,links"),
        api("/personal-export"),
      ]);
      const current = stateRef.current;
      await persist({
        ...current,
        enabledKinds: [
          "memories",
          "reminders",
          "documents",
          "purchases",
          "drawers",
          "links",
        ],
        entities: { ...current.entities, ...snapshot.entities },
        personalBudgets: personal.budgets,
      });
    } finally {
      active.current = false;
      setBusy(false);
    }
  }
  const filtered = state
    ? state.entities[
        tab === "reminders"
          ? "reminders"
          : tab === "documents"
            ? "documents"
            : "memories"
      ].filter((item) =>
        JSON.stringify(item)
          .toLocaleLowerCase()
          .includes(query.toLocaleLowerCase()),
      )
    : [];
  const conflicts = state ? Object.entries(state.conflicts) : [];
  return (
    <div className="app">
      <aside className={menu ? "sidebar open" : "sidebar"}>
        <Link to="/" className="brand">
          <div className="brand-symbol">S</div>
          <div>
            SALY<small>COFRE LOCAL</small>
          </div>
        </Link>
        <p className="workspace-label">
          SEU DISPOSITIVO · DADOS CRIPTOGRAFADOS
        </p>
        <nav>
          {[
            ["memories", "Memórias locais"],
            ["reminders", "Agenda local"],
            ["documents", "Documentos guardados"],
            ["personal", "Compras e Espaço locais"],
            ["books", "Livros guardados"],
            ["planning", "Agenda e alarmes guardados"],
            ["settings", "Cofre e sincronização"],
          ].map(([id, label]) => (
            <a
              href={"#" + id}
              key={id}
              className={tab === id ? "active" : ""}
              onClick={(event) => {
                event.preventDefault();
                setTab(id);
                setMenu(false);
                setEditing(null);
              }}
            >
              {label}
            </a>
          ))}
        </nav>
        <div className="sidebar-footer">
          <Link to="/">Voltar ao espaço online</Link>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <button
            className="icon-button"
            aria-label="Alternar menu local"
            onClick={() => setMenu(!menu)}
          >
            <Menu />
          </button>
          <span>SALY · {online ? "Rede detectada" : "Sem conexão"}</span>
          <span>
            <LockKeyhole size={14} />{" "}
            {key ? "Cofre desbloqueado" : "Cofre bloqueado"}
          </span>
        </header>
        <main>
          <div className="page-title">
            <small>CONTINUIDADE COM CONTROLE</small>
            <h1>Cofre local da SALY</h1>
            <p>
              Memórias, lembretes e documentos escolhidos. O modelo remoto
              precisa de internet; nenhum modelo local está instalado por esta
              função.
            </p>
          </div>
          {error && (
            <p className="notice" role="alert">
              {error}
            </p>
          )}
          {notice && <p role="status">{notice}</p>}
          {!key && (
            <section className="card">
              <h2>
                {exists
                  ? "Desbloquear dados locais"
                  : "Preparar este dispositivo"}
              </h2>
              <p>
                Este cofre é específico deste navegador e endereço. Guarde a
                senha e exporte backups; ela não pode ser recuperada pelo
                servidor. O navegador ainda pode limpar armazenamento.
              </p>
              <form
                onSubmit={async (event) => {
                  event.preventDefault();
                  setBusy(true);
                  setError("");
                  try {
                    const opened = exists
                      ? await unlockVault(password)
                      : consent
                        ? await createVault(
                            password,
                            await initialState(controller.current.signal),
                          )
                        : null;
                    if (!opened)
                      throw new Error(
                        "Autorize a cópia privada local antes de continuar.",
                      );
                    if (!exists && navigator.storage?.persist) {
                      const granted = await navigator.storage.persist();
                      setNotice(
                        granted
                          ? "Persistência de armazenamento concedida pelo navegador. Mantenha backups."
                          : "Cofre criado; o navegador não garantiu persistência de armazenamento. Mantenha backups.",
                      );
                    }
                    update(opened.state);
                    setKey(opened.key);
                    setExists(true);
                    setPassword("");
                  } catch (error) {
                    setError((error as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <label>
                  Senha do cofre
                  <input
                    type="password"
                    autoComplete="off"
                    minLength={8}
                    maxLength={200}
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                </label>
                {!exists && (
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={consent}
                      onChange={(event) => setConsent(event.target.checked)}
                    />
                    Autorizo copiar minhas memórias, lembretes e configurações
                    para este dispositivo e sincronizar alterações manuais
                    quando autenticada. Documentos originais só serão guardados
                    quando eu escolher.
                  </label>
                )}
                <button
                  disabled={busy || exists === null || (!exists && !consent)}
                >
                  {busy
                    ? "Verificando…"
                    : exists
                      ? "Desbloquear cofre"
                      : "Criar cofre criptografado"}
                </button>
              </form>
              <label className="file-button">
                Selecionar backup criptografado
                <input
                  type="file"
                  accept=".json"
                  disabled={busy}
                  onChange={async (event) => {
                    const file = event.target.files?.[0];
                    event.target.value = "";
                    if (!file) return;
                    try {
                      if (file.size > 65_000_000)
                        throw new Error("Backup excede 65 MB.");
                      setRestoration(JSON.parse(await file.text()));
                    } catch {
                      setError("Backup inválido ou grande demais.");
                    }
                  }}
                />
              </label>
              {restoration !== null && (
                <button
                  disabled={busy}
                  onClick={async () => {
                    if (
                      !confirm(
                        "Restaurar o cofre deste backup? O cofre atual será exportado antes da substituição. A senha acima deve ser a do backup.",
                      )
                    )
                      return;
                    setBusy(true);
                    setError("");
                    try {
                      if (exists)
                        download(
                          "saly-cofre-anterior-criptografado.json",
                          await encryptedBackup(),
                        );
                      await restoreBackup(restoration, password);
                      setExists(true);
                      setRestoration(null);
                      setPassword("");
                      setNotice(
                        "Backup validado e restaurado. Desbloqueie e revise a fila antes de sincronizar.",
                      );
                    } catch (error) {
                      setError((error as Error).message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Validar e restaurar backup
                </button>
              )}
            </section>
          )}
          {key && state && (
            <>
              <div className="toolbar">
                <span>
                  {state.pending.length} alterações pendentes ·{" "}
                  {conflicts.length} conflitos
                </span>
                <button
                  disabled={busy || !online || state.paused}
                  onClick={() => void sync()}
                >
                  Sincronizar agora
                </button>
                <button className="secondary" onClick={lock}>
                  Bloquear cofre
                </button>
              </div>
              {state.paused && (
                <section className="card">
                  <h2>Revisão após restauração</h2>
                  <p>
                    Confira a fila abaixo. Nenhuma operação será enviada
                    automaticamente antes da sua autorização.
                  </p>
                  <pre className="tool-result">
                    {JSON.stringify(
                      state.pending.map((item) => ({
                        entity: item.entity_type,
                        target: item.entity_id,
                        action: item.action,
                        payload: item.payload,
                      })),
                      null,
                      2,
                    )}
                  </pre>
                  <button
                    disabled={busy}
                    onClick={() => {
                      if (
                        confirm(
                          "Autorizar a sincronização destas operações restauradas, com validação de versão e alvo no servidor?",
                        )
                      )
                        void saveLocal({ ...state, paused: false });
                    }}
                  >
                    Autorizar fila revisada
                  </button>
                </section>
              )}
              {conflicts.map(([id, conflict]) => (
                <section className="card" key={id}>
                  <h2>Revisar conflito</h2>
                  <p>{conflict.detail}</p>
                  <p>Versão do servidor</p>
                  <pre className="tool-result">
                    {JSON.stringify(
                      conflict.record ?? "Registro excluído",
                      null,
                      2,
                    )}
                  </pre>
                  <p>Rascunho local</p>
                  <pre className="tool-result">
                    {JSON.stringify(
                      state.pending.find((item) => item.id === id)?.payload,
                      null,
                      2,
                    )}
                  </pre>
                  <button
                    disabled={busy}
                    onClick={() =>
                      void saveLocal(resolveConflict(state, id, false))
                    }
                  >
                    Manter versão do servidor
                  </button>
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() => {
                      if (
                        confirm(
                          conflict.deleted
                            ? "O registro foi excluído. Criar um novo registro a partir do rascunho local, com outro ID?"
                            : "Reenviar este rascunho sobre a versão do servidor apresentada?",
                        )
                      )
                        void saveLocal(resolveConflict(state, id, true));
                    }}
                  >
                    Usar rascunho local revisado
                  </button>
                </section>
              ))}
              {(tab === "memories" || tab === "reminders") && (
                <>
                  <h2>
                    {tab === "memories" ? "Memórias locais" : "Agenda local"}
                  </h2>
                  <p>
                    Pesquisa textual local. Alterações são rascunhos até
                    confirmação da sincronização.
                  </p>
                  <div className="toolbar">
                    <input
                      aria-label="Pesquisar cofre"
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                    />
                    <button
                      disabled={busy}
                      onClick={() =>
                        setEditing({
                          id: crypto.randomUUID().replaceAll("-", ""),
                          revision: 0,
                          content: "",
                          title: "",
                          category: "informacoes",
                          timezone: "America/Sao_Paulo",
                          due_at: "",
                        })
                      }
                    >
                      {tab === "memories"
                        ? "+ Memória local"
                        : "+ Lembrete local"}
                    </button>
                  </div>
                  {editing && (
                    <form
                      className="card"
                      onSubmit={(event) => {
                        event.preventDefault();
                        try {
                          const kind =
                            tab === "reminders" ? "reminders" : "memories";
                          if (
                            kind === "reminders" &&
                            !confirm(
                              `Salvar e sincronizar lembrete '${editing.title}' em ${editing.due_at} (${editing.timezone})?`,
                            )
                          )
                            return;
                          const data = payload(
                            editing,
                            kind === "memories" ? memoryFields : reminderFields,
                          );
                          void saveLocal(
                            queueEdit(
                              state,
                              kind,
                              editing.id,
                              data,
                              "upsert",
                              kind === "reminders",
                            ),
                          );
                        } catch (error) {
                          setError((error as Error).message);
                        }
                      }}
                    >
                      {tab === "memories" ? (
                        <>
                          <label>
                            Conteúdo da memória
                            <textarea
                              required
                              maxLength={20000}
                              value={String(editing.content ?? "")}
                              onChange={(event) =>
                                setEditing({
                                  ...editing,
                                  content: event.target.value,
                                })
                              }
                            />
                          </label>
                          <label>
                            Categoria
                            <input
                              maxLength={60}
                              value={String(editing.category ?? "informacoes")}
                              onChange={(event) =>
                                setEditing({
                                  ...editing,
                                  category: event.target.value,
                                })
                              }
                            />
                          </label>
                        </>
                      ) : (
                        <>
                          <label>
                            Título do lembrete
                            <input
                              required
                              maxLength={300}
                              value={String(editing.title ?? "")}
                              onChange={(event) =>
                                setEditing({
                                  ...editing,
                                  title: event.target.value,
                                })
                              }
                            />
                          </label>
                          <label>
                            Data e hora do lembrete
                            <input
                              type="datetime-local"
                              required
                              value={String(editing.due_at ?? "").slice(0, 16)}
                              onChange={(event) =>
                                setEditing({
                                  ...editing,
                                  due_at: event.target.value,
                                })
                              }
                            />
                          </label>
                          <label>
                            Fuso IANA
                            <input
                              value={String(
                                editing.timezone ?? "America/Sao_Paulo",
                              )}
                              onChange={(event) =>
                                setEditing({
                                  ...editing,
                                  timezone: event.target.value,
                                })
                              }
                            />
                          </label>
                        </>
                      )}
                      <button disabled={busy}>Salvar rascunho local</button>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => setEditing(null)}
                      >
                        Cancelar edição
                      </button>
                    </form>
                  )}
                  <div className="memory-grid">
                    {filtered.map((record) => (
                      <article className="card" key={record.id}>
                        <h3>
                          {String(record.title ?? record.category ?? "Memória")}
                        </h3>
                        <p>{String(record.content ?? record.due_at ?? "")}</p>
                        <small>
                          Revisão do servidor: {record.revision} ·{" "}
                          {state.pending.some(
                            (item) => item.entity_id === record.id,
                          )
                            ? "Alteração local pendente"
                            : "Cópia sincronizada"}
                        </small>
                        <div className="toolbar">
                          <button
                            disabled={busy}
                            onClick={() =>
                              setEditing(
                                tab === "reminders"
                                  ? {
                                      ...record,
                                      due_at: localDateTime(
                                        String(record.due_at ?? ""),
                                        String(
                                          record.timezone ??
                                            "America/Sao_Paulo",
                                        ),
                                      ),
                                    }
                                  : record,
                              )
                            }
                          >
                            Editar localmente
                          </button>
                          <button
                            className="danger"
                            disabled={busy}
                            onClick={() => {
                              if (
                                !confirm(
                                  "Excluir este registro e propagar a exclusão quando a sessão autenticada sincronizar?",
                                )
                              )
                                return;
                              try {
                                void saveLocal(
                                  queueEdit(
                                    state,
                                    tab === "reminders"
                                      ? "reminders"
                                      : "memories",
                                    record.id,
                                    {},
                                    "delete",
                                    true,
                                  ),
                                );
                              } catch (error) {
                                setError((error as Error).message);
                              }
                            }}
                          >
                            Excluir localmente
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                </>
              )}
              {tab === "documents" && (
                <>
                  <h2>Documentos guardados</h2>
                  <p>
                    Escolha quais originais e textos poderão permanecer neste
                    cofre. Não há inferência ou busca semântica offline.
                  </p>
                  {state.entities.documents.map((record) => (
                    <article className="card" key={record.id}>
                      <h3>{String(record.name)}</h3>
                      {state.documents[record.id] ? (
                        <>
                          <p>
                            Original e texto guardados de forma criptografada
                            neste dispositivo.
                          </p>
                          <details>
                            <summary>Texto extraído</summary>
                            <pre className="tool-result">
                              {String(
                                state.documents[record.id].record.content ??
                                  "Sem texto extraído; OCR não foi executado.",
                              )}
                            </pre>
                          </details>
                          <button
                            onClick={() => {
                              const stored = state.documents[record.id],
                                bytes = base64ToBytes(stored.originalBase64),
                                url = URL.createObjectURL(
                                  new Blob([bytes as BlobPart], {
                                    type: stored.mime,
                                  }),
                                );
                              const link = document.createElement("a");
                              link.href = url;
                              link.download = String(record.name);
                              link.click();
                              setTimeout(() => URL.revokeObjectURL(url), 1000);
                            }}
                          >
                            Baixar original local
                          </button>
                          <button
                            className="secondary"
                            disabled={busy}
                            onClick={() => {
                              const next = structuredClone(state);
                              delete next.documents[record.id];
                              void saveLocal(next);
                            }}
                          >
                            Remover cópia deste dispositivo
                          </button>
                        </>
                      ) : (
                        <button
                          disabled={busy || !online}
                          onClick={async () => {
                            if (
                              !confirm(
                                "Guardar uma cópia privada deste documento no dispositivo?",
                              )
                            )
                              return;
                            setBusy(true);
                            active.current = true;
                            setError("");
                            try {
                              const detail = await api(
                                "/knowledge/" + record.id,
                                { signal: controller.current.signal },
                              );
                              const response = await fetch(
                                `/api/knowledge/${record.id}/original`,
                                { signal: controller.current.signal },
                              );
                              if (!response.ok)
                                throw new Error(
                                  "Original indisponível ou sessão expirada.",
                                );
                              const blob = await response.blob();
                              if (blob.size > 10 * 1024 * 1024)
                                throw new Error(
                                  "Máximo de 10 MB por cópia local.",
                                );
                              const original = new Uint8Array(
                                await blob.arrayBuffer(),
                              );
                              const digest = Array.from(
                                new Uint8Array(
                                  await crypto.subtle.digest(
                                    "SHA-256",
                                    original as BufferSource,
                                  ),
                                ),
                                (byte) => byte.toString(16).padStart(2, "0"),
                              ).join("");
                              if (digest !== record.sha256)
                                throw new Error(
                                  "A integridade do original mudou. Sincronize os metadados e tente novamente.",
                                );
                              const next = structuredClone(state);
                              next.documents[record.id] = {
                                record: {
                                  ...detail,
                                  revision: record.revision,
                                },
                                originalBase64: bytesToBase64(original),
                                mime: blob.type,
                              };
                              await persist(next);
                            } catch (error) {
                              setError((error as Error).message);
                            } finally {
                              setBusy(false);
                              active.current = false;
                            }
                          }}
                        >
                          Guardar documento neste cofre
                        </button>
                      )}
                    </article>
                  ))}
                </>
              )}
              {tab === "planning" && (
                <OfflinePlanning
                  state={state}
                  save={saveLocal}
                  exclusive={exclusive}
                  busy={busy}
                  online={online}
                  fail={setError}
                />
              )}
              {tab === "books" && (
                <OfflineLibrary
                  state={state}
                  save={saveLocal}
                  exclusive={exclusive}
                  busy={busy}
                  online={online}
                  fail={setError}
                />
              )}
              {tab === "personal" && (
                <PersonalOffline
                  state={state}
                  save={saveLocal}
                  busy={busy}
                  online={online}
                  fail={setError}
                  enable={enablePersonal}
                />
              )}
              {tab === "settings" && (
                <section className="card">
                  <h2>Cofre e sincronização</h2>
                  <p>
                    Última sincronização:{" "}
                    {state.lastSync
                      ? new Date(state.lastSync).toLocaleString("pt-BR")
                      : "ainda não executada"}
                  </p>
                  <p>
                    Configurações copiadas do servidor para consulta; alterações
                    de configuração continuam no espaço online.
                  </p>
                  <details>
                    <summary>Configurações locais</summary>
                    <pre className="tool-result">
                      {JSON.stringify(state.preferences, null, 2)}
                    </pre>
                  </details>
                  <button
                    disabled={busy}
                    onClick={async () => {
                      try {
                        download(
                          "saly-cofre-criptografado.json",
                          await encryptedBackup(),
                        );
                      } catch (error) {
                        setError((error as Error).message);
                      }
                    }}
                  >
                    Exportar backup criptografado
                  </button>
                  <button
                    className="danger"
                    disabled={busy}
                    onClick={async () => {
                      if (
                        !confirm(
                          `Remover apenas este cofre local, incluindo ${state.pending.length} alterações ainda pendentes? Exporte um backup antes. O servidor não será apagado.`,
                        )
                      )
                        return;
                      try {
                        await clearVault();
                        lock();
                        setExists(false);
                      } catch (error) {
                        setError((error as Error).message);
                      }
                    }}
                  >
                    Remover cofre deste dispositivo
                  </button>
                </section>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
