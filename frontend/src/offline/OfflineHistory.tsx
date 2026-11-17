import { useState } from "react";
import { api } from "../api";
import type { VaultState } from "./vault";
export default function OfflineHistory({
  state,
  online,
  mutate,
  notify,
}: {
  state: VaultState;
  online: boolean;
  mutate: (
    operation: (current: VaultState) => Promise<VaultState>,
  ) => Promise<void>;
  notify: (message: string) => void;
}) {
  const [available, setAvailable] = useState<any[]>([]),
    [busy, setBusy] = useState(false);
  return (
    <section className="card">
      <h2>Histórico guardado</h2>
      <p>
        Cópias escolhidas por você, cifradas neste cofre. Até dez conversas, com
        as últimas cem mensagens e até 1 MB cada. Não geram respostas offline
        nem são sincronizadas de volta. Uma cópia antiga permanece até sua
        exclusão local.
      </p>
      <button
        disabled={!online || busy}
        onClick={async () => {
          try {
            setAvailable(await api("/conversations"));
          } catch (e) {
            notify((e as Error).message);
          }
        }}
      >
        Escolher conversa do servidor
      </button>
      {available.map((c) => (
        <div className="toolbar" key={c.id}>
          <span>{c.title}</span>
          <button
            disabled={busy || !online}
            onClick={async () => {
              setBusy(true);
              try {
                const snapshot = await api(`/conversations/${c.id}/snapshot`);
                await mutate(async (current) => {
                  const history = (current.history ?? []).filter(
                    (h) => h.id !== snapshot.id,
                  );
                  if (history.length >= 10)
                    throw new Error(
                      "Remova uma cópia: limite de dez conversas.",
                    );
                  return { ...current, history: [...history, snapshot] };
                });
              } catch (e) {
                notify((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            Guardar conversa no cofre
          </button>
        </div>
      ))}
      {(state.history ?? []).map((c) => (
        <details key={c.id}>
          <summary>
            {c.title} · cópia de {new Date(c.copiedAt).toLocaleString("pt-BR")}
          </summary>
          {c.messages.map((m, i) => (
            <article className="card" key={i}>
              <strong>{m.role === "user" ? "Você" : "SALY"}</strong>
              <p style={{ whiteSpace: "pre-wrap" }}>{m.content}</p>
            </article>
          ))}
          <button
            className="danger"
            disabled={busy}
            onClick={async () => {
              if (!confirm("Excluir apenas esta cópia de conversa do cofre?"))
                return;
              try {
                await mutate(async (current) => ({
                  ...current,
                  history: (current.history ?? []).filter((h) => h.id !== c.id),
                }));
              } catch (e) {
                notify((e as Error).message);
              }
            }}
          >
            Excluir cópia local da conversa
          </button>
        </details>
      ))}
      {!state.history?.length && (
        <p>Nenhuma conversa escolhida para acesso offline.</p>
      )}
    </section>
  );
}
