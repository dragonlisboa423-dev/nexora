import { useEffect, useState } from "react";
import { api, post, put } from "./api";
import { PageTitle, Empty } from "./Panels";
import { emit } from "./operations";
export function Approvals({
  notify,
  compact = false,
}: {
  notify: (s: string) => void;
  compact?: boolean;
}) {
  const [items, setItems] = useState<any[]>([]);
  const load = () =>
    api("/approvals")
      .then(setItems)
      .catch((e) => notify(e.message));
  useEffect(() => {
    void load();
    const t = setInterval(load, 3500);
    return () => clearInterval(t);
  }, []);
  const pending = items.filter((i) => i.status === "pending");
  return (
    <section
      className={compact ? "approval-dock" : "card"}
      aria-label="Aprovações pendentes"
    >
      {pending.length > 0 && (
        <h2>
          {pending.length}{" "}
          {pending.length === 1 ? "operação aguarda" : "operações aguardam"} sua
          decisão
        </h2>
      )}
      {pending.map((a) => (
        <article className="approval" key={a.id}>
          <span className="badge">NÃO EXECUTADA</span>
          <h3>{a.tool_name}</h3>
          <pre>{JSON.stringify(a.arguments, null, 2)}</pre>
          {a.preview?.summary && <p>Registro atual: {a.preview.summary}</p>}
          {a.preview?.diff && <pre>{a.preview.diff}</pre>}
          <small>
            Aprovação única · expira em 15 minutos. Revise o destino e os dados
            antes de autorizar.
          </small>
          <div className="toolbar">
            {[true, false].map((approve) => (
              <button
                key={String(approve)}
                className={approve ? "" : "secondary"}
                onClick={async () => {
                  if (approve && !confirm("Aprovar exatamente esta operação?"))
                    return;
                  emit({ type: "TOOL_STARTED", id: a.id });
                  try {
                    const r = await post("/approvals/" + a.id, { approve });
                    notify(
                      r.status === "completed"
                        ? "Operação confirmada e registrada."
                        : "Operação recusada.",
                    );
                    await load();
                  } catch (e) {
                    notify((e as Error).message);
                  } finally {
                    emit({ type: "TOOL_COMPLETED", id: a.id });
                  }
                }}
              >
                {approve ? "Aprovar operação" : "Recusar"}
              </button>
            ))}
          </div>
        </article>
      ))}
      {!compact && !pending.length && (
        <Empty text="Nenhuma operação aguardando aprovação." />
      )}
    </section>
  );
}
export function Tools({ notify }: { notify: (s: string) => void }) {
  const [tools, setTools] = useState<any[]>([]),
    [name, setName] = useState("calculate"),
    [args, setArgs] = useState('{"expression":"2+3*4"}'),
    [result, setResult] = useState("");
  useEffect(() => {
    api("/tools")
      .then(setTools)
      .catch((e) => notify(e.message));
  }, []);
  return (
    <>
      <PageTitle
        eyebrow="AGENTE · OPERAÇÕES CONTROLADAS"
        title="Ferramentas e integrações"
        text="Consultas permitidas e alterações revisáveis. Disponibilidade baseada na configuração real; nenhum comando de sistema é executado."
      />
      <Approvals notify={notify} />
      <div className="card">
        <h2>Executar uma ferramenta</h2>
        <label>
          Ferramenta
          <select value={name} onChange={(e) => setName(e.target.value)}>
            {tools.map((t) => (
              <option key={t.name} value={t.name} disabled={!t.available}>
                {t.name}
                {t.available ? "" : " · indisponível"}
              </option>
            ))}
          </select>
        </label>
        <p>{tools.find((t) => t.name === name)?.description}</p>
        <details>
          <summary>Esquema de argumentos</summary>
          <pre>
            {JSON.stringify(
              tools.find((t) => t.name === name)?.schema,
              null,
              2,
            )}
          </pre>
        </details>
        <label>
          Argumentos JSON
          <textarea value={args} onChange={(e) => setArgs(e.target.value)} />
        </label>
        <button
          onClick={async () => {
            emit({ type: "TOOL_STARTED", id: "manual-tool" });
            try {
              setResult(
                JSON.stringify(
                  await post("/tools/" + name, { arguments: JSON.parse(args) }),
                  null,
                  2,
                ),
              );
            } catch (e) {
              notify((e as Error).message);
            } finally {
              emit({ type: "TOOL_COMPLETED", id: "manual-tool" });
            }
          }}
        >
          Executar ou propor
        </button>
        {result && <pre className="tool-result">{result}</pre>}
      </div>
      <div className="memory-grid">
        {tools.map((t) => (
          <article className="card" key={t.name}>
            <h3>{t.name}</h3>
            <span className="badge">
              {t.available ? "Disponível" : "Não configurada"}
            </span>
            <p>{t.description}</p>
            <small>
              {t.approval_required
                ? "Exige aprovação explícita"
                : "Consulta automática permitida"}
            </small>
          </article>
        ))}
      </div>
    </>
  );
}
export function Agenda({ notify }: { notify: (s: string) => void }) {
  const [items, setItems] = useState<any[]>([]),
    [editing, setEditing] = useState<any>(null);
  const load = () =>
    api("/reminders")
      .then(setItems)
      .catch((e) => notify(e.message));
  useEffect(() => {
    void load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);
  return (
    <>
      <PageTitle
        eyebrow="CONTINUIDADE · AMERICA/SAO_PAULO"
        title="Agenda e lembretes"
        text="Agendamentos persistentes. Avisos são exibidos enquanto a aplicação estiver aberta; salvar um lembrete não significa que uma notificação foi entregue."
      />
      <button
        onClick={() =>
          setEditing({
            title: "",
            due_at: "",
            project: "",
            timezone: "America/Sao_Paulo",
            done: false,
          })
        }
      >
        + Novo lembrete
      </button>
      {editing && (
        <form
          className="card"
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              const body = {
                ...editing,
                due_at: editing.due_at,
              };
              delete body.id;
              delete body.created;
              delete body.updated;
              await (editing.id
                ? put("/reminders/" + editing.id, body)
                : post("/reminders", body));
              setEditing(null);
              notify("Proposta registrada. Revise e aprove a operação abaixo.");
            } catch (e) {
              notify((e as Error).message);
            }
          }}
        >
          <label>
            Título
            <input
              required
              value={editing.title}
              onChange={(e) =>
                setEditing({ ...editing, title: e.target.value })
              }
            />
          </label>
          <label>
            Data e hora no fuso selecionado
            <input
              type="datetime-local"
              required
              value={editing.due_at}
              onChange={(e) =>
                setEditing({ ...editing, due_at: e.target.value })
              }
            />
          </label>
          <label>
            Projeto
            <input
              value={editing.project}
              onChange={(e) =>
                setEditing({ ...editing, project: e.target.value })
              }
            />
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={editing.done}
              onChange={(e) =>
                setEditing({ ...editing, done: e.target.checked })
              }
            />
            Concluído
          </label>
          <button>Propor agendamento</button>
          <button
            type="button"
            className="secondary"
            onClick={() => setEditing(null)}
          >
            Cancelar
          </button>
        </form>
      )}
      <Approvals notify={notify} />
      {items.map((item) => (
        <article className="card document" key={item.id}>
          <div>
            <h2>{item.title}</h2>
            <p>
              {new Date(item.due_at).toLocaleString("pt-BR", {
                timeZone: item.timezone,
              })}{" "}
              · {item.timezone}
            </p>
            <small>
              {item.project} ·{" "}
              {item.done
                ? "Concluído"
                : new Date(item.due_at) < new Date()
                  ? "Horário atingido"
                  : "Agendado"}
            </small>
          </div>
          <div className="toolbar">
            <button
              className="secondary"
              onClick={() => {
                const display = new Intl.DateTimeFormat("sv-SE", {
                  timeZone: item.timezone,
                  dateStyle: "short",
                  timeStyle: "short",
                }).format(new Date(item.due_at));
                setEditing({ ...item, due_at: display.replace(" ", "T") });
              }}
            >
              Editar
            </button>
            <button
              className="danger"
              onClick={async () => {
                try {
                  await api("/reminders/" + item.id, { method: "DELETE" });
                  notify("Exclusão proposta. Aprove abaixo para confirmar.");
                } catch (e) {
                  notify((e as Error).message);
                }
              }}
            >
              Propor exclusão
            </button>
          </div>
        </article>
      ))}
      {!items.length && (
        <Empty text="Nenhum lembrete salvo. As propostas aparecem somente após aprovação." />
      )}
    </>
  );
}
export function ReminderAlerts({
  enabled,
  quietStart = "22:00",
  quietEnd = "08:00",
  timezone = "America/Sao_Paulo",
  minimumImportance = 0.5,
}: {
  enabled: boolean;
  quietStart?: string;
  quietEnd?: string;
  timezone?: string;
  minimumImportance?: number;
}) {
  const [due, setDue] = useState<any[]>([]);
  useEffect(() => {
    if (!enabled) {
      setDue([]);
      return;
    }
    const check = async () => {
      try {
        const items = await api("/reminders");
        const clock = new Date().toLocaleTimeString("pt-BR", {
          timeZone: timezone,
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        });
        const quiet =
          quietStart < quietEnd
            ? clock >= quietStart && clock < quietEnd
            : clock >= quietStart || clock < quietEnd;
        setDue(
          quiet
            ? []
            : items.filter(
                (r: any) =>
                  !r.done &&
                  (r.importance ?? 0.5) >= minimumImportance &&
                  new Date(r.due_at) <= new Date(),
              ),
        );
      } catch {
        /* No false notifications on connectivity failure. */
      }
    };
    void check();
    const t = setInterval(check, 30000);
    return () => clearInterval(t);
  }, [enabled, quietStart, quietEnd, timezone, minimumImportance]);
  return due.length ? (
    <div className="notice" role="status">
      {due.length} lembrete(s) com horário atingido:{" "}
      {due.map((r) => r.title).join(" · ")}. Consulte a Agenda.
    </div>
  ) : null;
}
