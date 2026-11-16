import { api } from "../api";
import { displayTime } from "../planning_time";
import type { VaultState } from "./vault";
export async function planningSnapshot() {
  const [events, alarms, occurrences] = await Promise.all([
    api("/calendar/events"),
    api("/alarms"),
    api("/alarms/occurrences"),
  ]);
  return { events, alarms, occurrences, copiedAt: new Date().toISOString() };
}
export default function OfflinePlanning({
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
  return (
    <section>
      <h2>Agenda e alarmes guardados</h2>
      <p>
        Fotografia criptografada para consulta. Alarmes não disparam por esta
        cópia e continuam dependendo do servidor/interface online. Edição de
        eventos e novos alarmes continua online; tarefas podem ser editadas em
        Agenda local.
      </p>
      {!state.planning ? (
        <button
          disabled={busy || !online}
          onClick={async () => {
            if (
              !confirm(
                "Autorizar copiar eventos, alarmes e histórico privado de ocorrências para este cofre?",
              )
            )
              return;
            try {
              await exclusive(async (current) => ({
                ...current,
                planning: await planningSnapshot(),
              }));
            } catch (e) {
              fail((e as Error).message);
            }
          }}
        >
          Guardar agenda e alarmes para consulta
        </button>
      ) : (
        <>
          <p>
            Atualizado em {state.planning.copiedAt}. A cópia é atualizada ao
            sincronizar com rede e sessão válidas.
          </p>
          <button
            disabled={busy}
            onClick={() => {
              if (
                confirm("Remover somente esta cópia local da agenda e alarmes?")
              )
                void save({ ...state, planning: undefined });
            }}
          >
            Remover cópia de agenda e alarmes
          </button>
          <h3>Eventos salvos</h3>
          {state.planning.events.map((event) => (
            <article className="card" key={event.id}>
              <h4>{event.title}</h4>
              <p>
                {displayTime(event.start_at, event.timezone)} —{" "}
                {displayTime(event.end_at, event.timezone)}
              </p>
              <p>
                {event.description} · {event.status}
              </p>
              <p>
                {event.recurrence_rule ?? "Evento único"} · {event.timezone}
              </p>
            </article>
          ))}
          <h3>Alarmes salvos</h3>
          {state.planning.alarms.map((alarm) => (
            <article className="card" key={alarm.id}>
              <h4>{alarm.title}</h4>
              <p>{alarm.message}</p>
              <p>
                {displayTime(alarm.scheduled_at, alarm.timezone)} ·{" "}
                {alarm.enabled ? "Ativado no servidor" : "Desativado"} ·{" "}
                {alarm.timezone}
              </p>
              <p>
                Próximo no servidor:{" "}
                {alarm.next_due_at
                  ? displayTime(alarm.next_due_at, alarm.timezone)
                  : "Sem próxima ocorrência"}
              </p>
            </article>
          ))}
          <details>
            <summary>Histórico de ocorrências copiado</summary>
            <pre className="tool-result">
              {JSON.stringify(state.planning.occurrences, null, 2)}
            </pre>
          </details>
        </>
      )}
    </section>
  );
}
