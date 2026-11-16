import { useEffect, useRef, useState } from "react";
import { api, post, type Prefs } from "./api";
import { Agenda } from "./AgentPanels";
import { PageTitle } from "./Panels";
import {
  addDays,
  dayInZone,
  displayTime,
  localDateTime,
  weekStart,
} from "./planning_time";
import {
  alarmAudioReady,
  enableAlarmAudio,
  playAlarmTone,
  stopAlarmAudio,
} from "./alarm_audio";
import type { AlarmOccurrence } from "./AlarmNotifier";

type EventData = {
  title: string;
  description: string;
  start_at: string;
  end_at: string;
  timezone: string;
  location: string;
  category: string;
  color: string;
  priority: string;
  recurrence_rule: string | null;
  notes: string;
  checklist: string[];
  status: string;
  all_day: boolean;
  alarm_minutes_before: number | null;
  allow_conflicts: boolean;
};
type CalendarRecord = EventData & {
  id: string;
  revision: number;
  instance_id?: string;
  instance_start_at?: string;
  instance_end_at?: string;
};
type AlarmData = {
  title: string;
  message: string;
  scheduled_at: string;
  timezone: string;
  recurrence_rule: string | null;
  enabled: boolean;
  mode: string;
  sound_id: string;
  priority: string;
  snooze_minutes: number;
  linked_event_id: string | null;
  linked_event_revision: number | null;
  offset_minutes: number;
};
type AlarmRecord = AlarmData & {
  id: string;
  revision: number;
  next_due_at?: string | null;
};
const eventFields: (keyof EventData)[] = [
  "title",
  "description",
  "start_at",
  "end_at",
  "timezone",
  "location",
  "category",
  "color",
  "priority",
  "recurrence_rule",
  "notes",
  "checklist",
  "status",
  "all_day",
  "alarm_minutes_before",
  "allow_conflicts",
];
const alarmFields: (keyof AlarmData)[] = [
  "title",
  "message",
  "scheduled_at",
  "timezone",
  "recurrence_rule",
  "enabled",
  "mode",
  "sound_id",
  "priority",
  "snooze_minutes",
  "linked_event_id",
  "linked_event_revision",
  "offset_minutes",
];
function pick<T extends object>(value: T, keys: (keyof T)[]) {
  return Object.fromEntries(keys.map((key) => [key, value[key]]));
}
function changed() {
  window.dispatchEvent(new Event("saly-alarms-changed"));
}

function RecurrenceEditor({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (rule: string | null) => void;
}) {
  const options: Record<string, string | null> = {
    once: null,
    daily: "FREQ=DAILY",
    weekly: "FREQ=WEEKLY",
    monthly: "FREQ=MONTHLY",
  };
  const [mode, setMode] = useState(
    Object.entries(options).find(([, rule]) => rule === value)?.[0] ?? "custom",
  );
  return (
    <>
      <label>
        Repetição
        <select
          aria-label="Repetição"
          value={mode}
          onChange={(event) => {
            const selected = event.target.value;
            setMode(selected);
            onChange(
              selected in options
                ? options[selected]
                : (value ?? "FREQ=WEEKLY;BYDAY=MO,WE,FR"),
            );
          }}
        >
          <option value="once">Uma vez</option>
          <option value="daily">Diariamente</option>
          <option value="weekly">Semanalmente</option>
          <option value="monthly">Mensalmente</option>
          <option value="custom">
            Dias selecionados / regra personalizada
          </option>
        </select>
      </label>
      {mode === "custom" && (
        <label>
          Regra RRULE
          <input
            maxLength={300}
            value={value ?? ""}
            onChange={(event) => onChange(event.target.value || null)}
          />
          <small>
            Ex.: FREQ=WEEKLY;BYDAY=MO,WE,FR ou FREQ=MONTHLY;BYMONTHDAY=-1. O
            início deve corresponder ao padrão. Campos e limites são validados
            no servidor.
          </small>
        </label>
      )}
      <small>
        Confira a prévia. Datas inexistentes no mês e horários futuros
        ambíguos/inexistentes por mudança de fuso são pulados, não transferidos
        silenciosamente.
      </small>
    </>
  );
}

export function PlanningPage({
  notify,
  timezone = "America/Sao_Paulo",
}: {
  notify: (message: string) => void;
  timezone?: string;
}) {
  const [day, setDay] = useState(dayInZone(timezone)),
    [view, setView] = useState("month"),
    [items, setItems] = useState<CalendarRecord[]>([]),
    [records, setRecords] = useState<CalendarRecord[]>([]),
    [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<CalendarRecord | null>(null),
    [preview, setPreview] = useState<{
      event: EventData;
      conflicts: {
        id: string;
        title: string;
        start_at: string;
        end_at: string;
      }[];
      scope: string;
    } | null>(null);
  const from =
    view === "month"
      ? weekStart(day.slice(0, 7) + "-01")
      : view === "week"
        ? weekStart(day)
        : day;
  const count =
    view === "month" ? 42 : view === "week" ? 7 : view === "day" ? 1 : 30;
  const loadVersion = useRef(0);
  async function load() {
    const version = ++loadVersion.current;
    const [instances, all] = await Promise.all([
      api(
        `/calendar/instances?date_from=${from}&date_to=${addDays(from, count)}&timezone=${encodeURIComponent(timezone)}`,
      ),
      api("/calendar/events"),
    ]);
    if (version !== loadVersion.current) return;
    setItems(instances);
    setRecords(all);
  }
  useEffect(() => {
    load().catch((error) => notify(error.message));
  }, [from, count, timezone]);
  function edit(record?: CalendarRecord, date = day) {
    setPreview(null);
    setEditing(
      record
        ? {
            ...record,
            start_at: localDateTime(record.start_at, record.timezone),
            end_at: localDateTime(record.end_at, record.timezone),
          }
        : {
            id: "",
            revision: 0,
            title: "",
            description: "",
            start_at: date + "T13:00",
            end_at: date + "T14:00",
            timezone,
            location: "",
            category: "pessoal",
            color: "#7acfc1",
            priority: "normal",
            recurrence_rule: null,
            notes: "",
            checklist: [],
            status: "scheduled",
            all_day: false,
            alarm_minutes_before: null,
            allow_conflicts: false,
          },
    );
  }
  async function review() {
    if (!editing) return;
    setBusy(true);
    try {
      setPreview(
        await post(
          "/calendar/preview" + (editing.id ? "?key=" + editing.id : ""),
          { data: pick(editing, eventFields), base_revision: editing.revision },
        ),
      );
    } catch (error) {
      notify((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function save() {
    if (
      !editing ||
      !preview ||
      !confirm(
        "Salvar exatamente este evento, horário, repetição e eventual alarme?",
      )
    )
      return;
    setBusy(true);
    try {
      await api("/calendar/events" + (editing.id ? "/" + editing.id : ""), {
        method: editing.id ? "PATCH" : "POST",
        body: JSON.stringify({
          data: pick(editing, eventFields),
          base_revision: editing.revision,
          confirm: true,
        }),
      });
      setEditing(null);
      setPreview(null);
      await load();
      changed();
    } catch (error) {
      notify((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function eventCard(item: CalendarRecord) {
    const record = records.find((record) => record.id === item.id) ?? item;
    return (
      <button
        key={item.instance_id ?? item.id}
        className="calendar-entry"
        style={{ borderLeftColor: item.color }}
        onClick={() => edit(record)}
      >
        <strong>{item.title}</strong>
        <small>
          {displayTime(item.instance_start_at ?? item.start_at, timezone)} ·{" "}
          {item.priority === "high"
            ? "Alta"
            : item.priority === "low"
              ? "Baixa"
              : "Normal"}
        </small>
      </button>
    );
  }
  return (
    <>
      <PageTitle
        eyebrow="TEMPO · PLANOS SOB SEU CONTROLE"
        title="Agenda inteligente"
        text="Eventos reais, tarefas, fusos e alarmes opcionais. Sugestões e alterações precisam da sua revisão; nenhuma agenda externa é presumida."
      />
      <div className="toolbar">
        <label>
          Data de referência
          <input
            type="date"
            value={day}
            onChange={(event) => {
              if (event.target.value) setDay(event.target.value);
            }}
          />
        </label>
        <label>
          Visualização da agenda
          <select
            aria-label="Visualização da agenda"
            value={view}
            onChange={(event) => setView(event.target.value)}
          >
            <option value="day">Dia</option>
            <option value="week">Semana</option>
            <option value="month">Mês</option>
            <option value="list">Lista a partir da data · 30 dias</option>
          </select>
        </label>
        <button onClick={() => edit()}>+ Novo evento</button>
      </div>
      <p>
        Fuso da visualização: {timezone}. Eventos podem usar outro fuso, que
        permanece registrado.
      </p>
      {view === "list" ? (
        <div className="card">
          {items.map(eventCard)}
          {!items.length && <p>Nenhum evento neste período.</p>}
        </div>
      ) : (
        <div
          className={view === "day" ? "calendar-day-view" : "calendar-grid"}
          aria-label="Calendário de eventos"
        >
          {Array.from({ length: count }, (_, index) =>
            addDays(from, index),
          ).map((date) => (
            <section className="calendar-cell" key={date}>
              <button
                className="text-button"
                onClick={() => edit(undefined, date)}
                aria-label={"Criar evento em " + date}
              >
                {new Date(date + "T12:00:00Z").toLocaleDateString("pt-BR", {
                  day: "2-digit",
                  month: "2-digit",
                  weekday: "short",
                  timeZone: "UTC",
                })}
              </button>
              {items
                .filter(
                  (item) =>
                    localDateTime(
                      item.instance_start_at ?? item.start_at,
                      timezone,
                    ).slice(0, 10) === date,
                )
                .map(eventCard)}
            </section>
          ))}
        </div>
      )}
      {editing && (
        <form
          className="card"
          onSubmit={(event) => {
            event.preventDefault();
            void review();
          }}
        >
          <h2>{editing.id ? "Editar evento" : "Criar evento"}</h2>
          <label>
            Título do evento
            <input
              required
              maxLength={300}
              value={editing.title}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, title: event.target.value });
              }}
            />
          </label>
          <label>
            Descrição do evento
            <textarea
              maxLength={5000}
              value={editing.description}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, description: event.target.value });
              }}
            />
          </label>
          <div className="form-grid">
            <label>
              Início do evento
              <input
                type="datetime-local"
                required
                value={editing.start_at}
                onChange={(event) => {
                  setPreview(null);
                  setEditing({ ...editing, start_at: event.target.value });
                }}
              />
            </label>
            <label>
              Fim do evento
              <input
                type="datetime-local"
                required
                value={editing.end_at}
                onChange={(event) => {
                  setPreview(null);
                  setEditing({ ...editing, end_at: event.target.value });
                }}
              />
            </label>
          </div>
          <label>
            Fuso do evento
            <input
              required
              value={editing.timezone}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, timezone: event.target.value });
              }}
            />
          </label>
          <label>
            Local do evento
            <input
              maxLength={300}
              value={editing.location}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, location: event.target.value });
              }}
            />
          </label>
          <div className="form-grid">
            <label>
              Categoria do evento
              <input
                maxLength={60}
                value={editing.category}
                onChange={(event) => {
                  setPreview(null);
                  setEditing({ ...editing, category: event.target.value });
                }}
              />
            </label>
            <label>
              Cor do evento
              <input
                type="color"
                value={editing.color}
                onChange={(event) => {
                  setPreview(null);
                  setEditing({ ...editing, color: event.target.value });
                }}
              />
            </label>
          </div>
          <label>
            Prioridade do evento
            <select
              value={editing.priority}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, priority: event.target.value });
              }}
            >
              <option value="low">Baixa</option>
              <option value="normal">Normal</option>
              <option value="high">Alta</option>
            </select>
          </label>
          <RecurrenceEditor
            key={editing.id || "new-event"}
            value={editing.recurrence_rule}
            onChange={(rule) => {
              setPreview(null);
              setEditing({ ...editing, recurrence_rule: rule });
            }}
          />
          <label>
            Estado do evento
            <select
              value={editing.status}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, status: event.target.value });
              }}
            >
              <option value="scheduled">Agendado</option>
              <option value="completed">Concluído</option>
              <option value="cancelled">Cancelado</option>
            </select>
          </label>
          <label>
            Observações
            <textarea
              maxLength={5000}
              value={editing.notes}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, notes: event.target.value });
              }}
            />
          </label>
          <label>
            Checklist · um item por linha
            <textarea
              value={editing.checklist.join("\n")}
              onChange={(event) => {
                setPreview(null);
                setEditing({
                  ...editing,
                  checklist: event.target.value
                    .split("\n")
                    .filter(Boolean)
                    .slice(0, 100),
                });
              }}
            />
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={editing.alarm_minutes_before !== null}
              onChange={(event) => {
                setPreview(null);
                setEditing({
                  ...editing,
                  alarm_minutes_before: event.target.checked ? 15 : null,
                });
              }}
            />
            Associar alarme opcional
          </label>
          {editing.alarm_minutes_before !== null && (
            <label>
              Minutos antes
              <input
                type="number"
                min={0}
                max={10080}
                value={editing.alarm_minutes_before}
                onChange={(event) => {
                  setPreview(null);
                  setEditing({
                    ...editing,
                    alarm_minutes_before: Number(event.target.value),
                  });
                }}
              />
            </label>
          )}
          <button disabled={busy}>Verificar prévia e conflitos</button>
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setEditing(null);
              setPreview(null);
            }}
          >
            Cancelar evento
          </button>
          {editing.id && (
            <button
              type="button"
              className="danger"
              disabled={busy}
              onClick={async () => {
                if (
                  !confirm(
                    "Excluir este evento e cancelar os alarmes associados?",
                  )
                )
                  return;
                try {
                  await api(`/calendar/events/${editing.id}?confirm=true`, {
                    method: "DELETE",
                  });
                  setEditing(null);
                  setPreview(null);
                  await load();
                  changed();
                } catch (error) {
                  notify((error as Error).message);
                }
              }}
            >
              Excluir evento
            </button>
          )}
          {preview && (
            <section aria-label="Prévia do evento">
              <h3>Conferir evento</h3>
              <p>
                {displayTime(preview.event.start_at, preview.event.timezone)} →{" "}
                {displayTime(preview.event.end_at, preview.event.timezone)} ·{" "}
                {preview.event.timezone}
              </p>
              <p>{preview.scope}</p>
              {preview.conflicts.map((item) => (
                <p key={item.id + item.start_at}>
                  Conflito: {item.title} ·{" "}
                  {displayTime(item.start_at, timezone)}
                </p>
              ))}
              {preview.conflicts.length > 0 && (
                <label className="check">
                  <input
                    type="checkbox"
                    checked={editing.allow_conflicts}
                    onChange={(event) =>
                      setEditing({
                        ...editing,
                        allow_conflicts: event.target.checked,
                      })
                    }
                  />
                  Autorizo salvar mesmo com estas sobreposições
                </label>
              )}
              <button
                type="button"
                disabled={
                  busy ||
                  (preview.conflicts.length > 0 && !editing.allow_conflicts)
                }
                onClick={() => void save()}
              >
                Confirmar evento e alarme
              </button>
            </section>
          )}
        </form>
      )}
      <section className="card">
        <h2>Próximos compromissos</h2>
        {items
          .filter(
            (item) =>
              new Date(item.instance_end_at ?? item.end_at) > new Date(),
          )
          .slice(0, 8)
          .map(eventCard)}
        {!items.length && <p>Sem compromissos no intervalo exibido.</p>}
      </section>
      <Agenda notify={notify} embedded />
    </>
  );
}

export function AlarmsPage({
  notify,
  prefs,
  save,
}: {
  notify: (message: string) => void;
  prefs: Prefs;
  save: (prefs: Prefs) => Promise<void>;
}) {
  const timezone = prefs.notifications?.timezone ?? "America/Sao_Paulo";
  const [schedulerObserved, setSchedulerObserved] = useState<{
    running: boolean;
    last_check: string | null;
    last_error: string | null;
  } | null>(null);
  const alarmLoadVersion = useRef(0);
  const [items, setItems] = useState<AlarmRecord[]>([]),
    [history, setHistory] = useState<AlarmOccurrence[]>([]),
    [events, setEvents] = useState<CalendarRecord[]>([]),
    [editing, setEditing] = useState<AlarmRecord | null>(null),
    [preview, setPreview] = useState<{
      alarm: AlarmData;
      next_occurrences: string[];
      warning: string;
    } | null>(null),
    [busy, setBusy] = useState(false),
    [soundReady, setSoundReady] = useState(alarmAudioReady()),
    [permission, setPermission] = useState(
      "Notification" in window ? Notification.permission : "unsupported",
    );
  async function load() {
    const version = ++alarmLoadVersion.current;
    const [alarms, occurrences, calendar, capabilities] = await Promise.all([
      api("/alarms"),
      api("/alarms/occurrences"),
      api("/calendar/events"),
      api("/notifications/capabilities"),
    ]);
    if (version !== alarmLoadVersion.current) return;
    setItems(alarms);
    setHistory(occurrences);
    setEvents(calendar);
    setSchedulerObserved(capabilities.scheduler_observed);
  }
  useEffect(() => {
    load().catch((error) => notify(error.message));
    const timer = setInterval(() => load().catch(() => {}), 15000);
    return () => clearInterval(timer);
  }, []);
  function edit(record?: AlarmRecord) {
    setPreview(null);
    setEditing(
      record
        ? {
            ...record,
            scheduled_at: localDateTime(record.scheduled_at, record.timezone),
          }
        : {
            id: "",
            revision: 0,
            title: "",
            message: "",
            scheduled_at: dayInZone(timezone) + "T13:00",
            timezone,
            recurrence_rule: null,
            enabled: true,
            mode: "tone",
            sound_id: "soft",
            priority: "normal",
            snooze_minutes: 5,
            linked_event_id: null,
            linked_event_revision: null,
            offset_minutes: 0,
          },
    );
  }
  return (
    <>
      <PageTitle
        eyebrow="OPCIONAIS · HORÁRIOS E CAPACIDADES REAIS"
        title="Alarmes"
        text="Agenda e alarmes independentes com histórico persistente. A PWA não garante horário exato com navegador fechado, sem rede ou com o servidor suspenso."
      />
      <section className="card">
        <h2>Capacidade deste ambiente</h2>
        <p>
          Disponível: alarme na interface aberta com backend ativo. Web Push e
          alarme nativo não configurados. O processo do backend foi programado
          para consultas a cada 15 segundos; o estado observado aparece abaixo.
        </p>
        <p>
          Agendador:{" "}
          {schedulerObserved?.running
            ? "ativo no backend"
            : "não observado / parado"}
          . Última consulta confirmada:{" "}
          {schedulerObserved?.last_check
            ? new Date(schedulerObserved.last_check).toLocaleString("pt-BR")
            : "nenhuma"}
          .{" "}
          {schedulerObserved?.last_error &&
            "A última consulta não foi confirmada."}
        </p>
        <label className="check">
          <input
            type="checkbox"
            checked={prefs.notifications?.enabled ?? false}
            onChange={(event) =>
              void save({
                ...prefs,
                notifications: {
                  enabled: event.target.checked,
                  quietStart: prefs.notifications?.quietStart ?? "22:00",
                  quietEnd: prefs.notifications?.quietEnd ?? "08:00",
                  timezone,
                  minimumImportance:
                    prefs.notifications?.minimumImportance ?? 0.5,
                },
              })
            }
          />
          Permitir avisos de alarmes e lembretes nesta interface
        </label>
        <p>
          Permissão de notificação: {permission}. Som nesta aba:{" "}
          {soundReady ? "habilitado por interação" : "ainda não habilitado"}.
          Alarmes explícitos seguem os horários escolhidos; não são promessas de
          despertador nativo.
        </p>
        <div className="toolbar">
          <button
            className="secondary"
            disabled={permission === "unsupported"}
            onClick={async () =>
              setPermission(await Notification.requestPermission())
            }
          >
            Solicitar notificações do navegador
          </button>
          <button
            className="secondary"
            onClick={async () => {
              try {
                setSoundReady(await enableAlarmAudio());
                playAlarmTone("soft");
              } catch (error) {
                notify((error as Error).message);
              }
            }}
          >
            Habilitar e testar toque nesta aba
          </button>
          <button className="secondary" onClick={stopAlarmAudio}>
            Parar toque
          </button>
          <button
            disabled={!prefs.notifications?.enabled || busy}
            onClick={async () => {
              if (
                !confirm(
                  "Criar uma ocorrência real de teste silencioso para a interface?",
                )
              )
                return;
              setBusy(true);
              try {
                await post("/notifications/test", {
                  confirm: true,
                  mode: "silent",
                });
                changed();
                await load();
              } catch (error) {
                notify((error as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            Testar apresentação de alarme
          </button>
        </div>
      </section>
      <button onClick={() => edit()}>+ Novo alarme</button>
      {editing && (
        <form
          className="card"
          onSubmit={async (event) => {
            event.preventDefault();
            setBusy(true);
            try {
              setPreview(
                await post("/alarms/preview", {
                  data: pick(editing, alarmFields),
                }),
              );
            } catch (error) {
              notify((error as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <h2>{editing.id ? "Editar alarme" : "Criar alarme"}</h2>
          <label>
            Título do alarme
            <input
              required
              maxLength={300}
              value={editing.title}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, title: event.target.value });
              }}
            />
          </label>
          <label>
            Mensagem do alarme
            <textarea
              maxLength={1000}
              value={editing.message}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, message: event.target.value });
              }}
            />
          </label>
          <label>
            Data e hora do alarme
            <input
              type="datetime-local"
              required
              value={editing.scheduled_at}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, scheduled_at: event.target.value });
              }}
            />
          </label>
          <label>
            Fuso do alarme
            <input
              required
              value={editing.timezone}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, timezone: event.target.value });
              }}
            />
          </label>
          <label>
            Evento associado
            <select
              value={editing.linked_event_id ?? ""}
              onChange={(event) => {
                const selected = events.find(
                  (item) => item.id === event.target.value,
                );
                setPreview(null);
                setEditing({
                  ...editing,
                  linked_event_id: selected?.id ?? null,
                  linked_event_revision: selected?.revision ?? null,
                  scheduled_at: selected
                    ? localDateTime(selected.start_at, selected.timezone)
                    : editing.scheduled_at,
                  timezone: selected?.timezone ?? editing.timezone,
                  recurrence_rule: selected ? null : editing.recurrence_rule,
                });
              }}
            >
              <option value="">Alarme independente</option>
              {events
                .filter((event) => event.status !== "cancelled")
                .map((event) => (
                  <option value={event.id} key={event.id}>
                    {event.title} ·{" "}
                    {displayTime(event.start_at, event.timezone)}
                  </option>
                ))}
            </select>
          </label>
          {editing.linked_event_id ? (
            <label>
              Minutos antes do evento
              <input
                type="number"
                min={0}
                max={10080}
                value={editing.offset_minutes}
                onChange={(event) => {
                  setPreview(null);
                  setEditing({
                    ...editing,
                    offset_minutes: Number(event.target.value),
                  });
                }}
              />
            </label>
          ) : (
            <RecurrenceEditor
              key={editing.id || "new-alarm"}
              value={editing.recurrence_rule}
              onChange={(rule) => {
                setPreview(null);
                setEditing({ ...editing, recurrence_rule: rule });
              }}
            />
          )}
          <label>
            Modo do alarme
            <select
              aria-label="Modo do alarme"
              value={editing.mode}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, mode: event.target.value });
              }}
            >
              <option value="tone">Toque</option>
              <option value="voice">Voz selecionada da SALY</option>
              <option value="tone_voice">Toque e voz</option>
              <option value="silent">Aviso silencioso</option>
            </select>
          </label>
          <label>
            Toque
            <select
              value={editing.sound_id}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, sound_id: event.target.value });
              }}
            >
              <option value="soft">Suave</option>
              <option value="bell">Sino sintético</option>
              <option value="pulse">Pulso sintético</option>
            </select>
          </label>
          <label>
            Prioridade do alarme
            <select
              value={editing.priority}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, priority: event.target.value });
              }}
            >
              <option value="low">Baixa</option>
              <option value="normal">Normal</option>
              <option value="high">Alta</option>
            </select>
          </label>
          <label>
            Adiar por quantos minutos
            <input
              type="number"
              min={1}
              max={120}
              value={editing.snooze_minutes}
              onChange={(event) => {
                setPreview(null);
                setEditing({
                  ...editing,
                  snooze_minutes: Number(event.target.value),
                });
              }}
            />
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={editing.enabled}
              onChange={(event) => {
                setPreview(null);
                setEditing({ ...editing, enabled: event.target.checked });
              }}
            />
            Alarme ativado
          </label>
          <button disabled={busy}>Verificar prévia do alarme</button>
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setEditing(null);
              setPreview(null);
            }}
          >
            Cancelar alarme
          </button>
          {preview && (
            <section aria-label="Prévia do alarme">
              <h3>Conferir próximas ocorrências</h3>
              <p>{preview.warning}</p>
              {preview.next_occurrences.map((value) => (
                <p key={value}>
                  {displayTime(value, preview.alarm.timezone)} ·{" "}
                  {preview.alarm.timezone}
                </p>
              ))}
              <button
                type="button"
                disabled={busy}
                onClick={async () => {
                  if (
                    !confirm(
                      "Salvar exatamente este alarme, horário, mensagem, repetição e modo?",
                    )
                  )
                    return;
                  setBusy(true);
                  try {
                    await api(
                      "/alarms" + (editing.id ? "/" + editing.id : ""),
                      {
                        method: editing.id ? "PATCH" : "POST",
                        body: JSON.stringify({
                          data: pick(editing, alarmFields),
                          base_revision: editing.revision,
                          confirm: true,
                        }),
                      },
                    );
                    setEditing(null);
                    setPreview(null);
                    changed();
                    await load();
                  } catch (error) {
                    notify((error as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Confirmar alarme
              </button>
            </section>
          )}
        </form>
      )}
      <div className="memory-grid">
        {items.map((item) => (
          <article className="card" key={item.id}>
            <h2>{item.title}</h2>
            <p>
              {displayTime(item.scheduled_at, item.timezone)} · {item.timezone}
            </p>
            <p>{item.message}</p>
            <small>
              {item.enabled ? "Ativado" : "Desativado / sem próxima ocorrência"}{" "}
              · {item.recurrence_rule ?? "Uma vez"} · {item.mode}
            </small>
            <p>
              Próxima ocorrência:{" "}
              {item.next_due_at
                ? displayTime(item.next_due_at, item.timezone)
                : "nenhuma"}
            </p>
            <div className="toolbar">
              <button className="secondary" onClick={() => edit(item)}>
                Editar alarme
              </button>
              <button
                className="danger"
                onClick={async () => {
                  if (
                    !confirm("Excluir este alarme e cancelar avisos pendentes?")
                  )
                    return;
                  try {
                    await api(`/alarms/${item.id}?confirm=true`, {
                      method: "DELETE",
                    });
                    changed();
                    await load();
                  } catch (error) {
                    notify((error as Error).message);
                  }
                }}
              >
                Excluir alarme
              </button>
            </div>
          </article>
        ))}
      </div>
      {!items.length && (
        <p>Nenhum alarme configurado. Notificações não foram presumidas.</p>
      )}
      <section className="card">
        <h2>Histórico de ocorrências</h2>
        {history.map((item) => (
          <article key={item.id}>
            <h3>{item.title}</h3>
            <p>
              {displayTime(item.scheduled_at, timezone)} ·{" "}
              {(
                {
                  pending: "Aguardando apresentação",
                  queued: "Adiado",
                  claimed: "Em apresentação",
                  presented: "Apresentação reportada pela interface",
                  missed: "Perdido/atrasado · entrega não confirmada",
                  dismissed: "Concluído",
                  snoozed: "Adiado para outra ocorrência",
                  cancelled: "Cancelado",
                } as Record<string, string>
              )[item.status] ?? item.status}
            </p>
            {["pending", "claimed", "presented", "missed"].includes(
              item.status,
            ) && (
              <button
                className="secondary"
                onClick={async () => {
                  try {
                    await post(`/alarm-occurrences/${item.id}/dismiss`);
                    changed();
                    await load();
                  } catch (error) {
                    notify((error as Error).message);
                  }
                }}
              >
                Concluir ocorrência
              </button>
            )}
          </article>
        ))}
        {!history.length && <p>Nenhuma ocorrência processada.</p>}
      </section>
    </>
  );
}
