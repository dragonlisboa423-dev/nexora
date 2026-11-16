import { useEffect, useRef, useState } from "react";
import { api, post } from "./api";
import { playAlarmTone, stopAlarmAudio } from "./alarm_audio";

export type AlarmOccurrence = {
  id: string;
  alarm_id: string;
  title: string;
  message: string;
  scheduled_at: string;
  status: string;
  mode: string;
  sound_id: string;
  snooze_minutes: number;
  delivery: string;
};
export function AlarmNotifier({
  enabled,
  speak,
  stop,
}: {
  enabled: boolean;
  speak: (text: string) => void;
  stop: () => void;
}) {
  const [items, setItems] = useState<AlarmOccurrence[]>([]),
    [error, setError] = useState("");
  const seen = useRef(new Set<string>()),
    callbacks = useRef({ speak, stop });
  callbacks.current = { speak, stop };
  useEffect(() => {
    if (!enabled) {
      setItems([]);
      return;
    }
    let alive = true,
      checking = false,
      refreshWanted = false;
    const controller = new AbortController();
    async function check() {
      if (checking) {
        refreshWanted = true;
        return;
      }
      checking = true;
      try {
        const pending: AlarmOccurrence[] = await api(
          "/alarms/occurrences?active=true",
          { signal: controller.signal },
        );
        if (!alive) return;
        const ids = new Set(pending.map((item) => item.id));
        setItems((previous) => previous.filter((item) => ids.has(item.id)));
        setError("");
        for (const item of pending) {
          if (!alive || seen.current.has(item.id)) continue;
          if (item.status === "presented") {
            seen.current.add(item.id);
            setItems((previous) => [
              ...previous.filter((other) => other.id !== item.id),
              item,
            ]);
            continue;
          }
          try {
            const claimed = await post(`/alarm-occurrences/${item.id}/claim`);
            if (!alive) return;
            seen.current.add(item.id);
            setItems((previous) => [
              ...previous.filter((other) => other.id !== item.id),
              item,
            ]);
            let notificationRequested = false,
              audioStarted = false;
            if (
              "Notification" in window &&
              Notification.permission === "granted"
            ) {
              try {
                new Notification(item.title, {
                  body: item.message,
                  tag: item.id,
                });
                notificationRequested = true;
              } catch {}
            }
            if (item.mode === "tone" || item.mode === "tone_voice")
              audioStarted = playAlarmTone(item.sound_id);
            const voiceRequested =
              item.mode === "voice" || item.mode === "tone_voice";
            if (voiceRequested)
              callbacks.current.speak(item.title + ". " + item.message);
            await post(`/alarm-occurrences/${item.id}/presented`, {
              claim_token: claimed.claim_token,
              notification_requested: notificationRequested,
              audio_started: audioStarted,
              voice_requested: voiceRequested,
            });
          } catch (error) {
            if (!String((error as Error).message).includes("Ocorrência já"))
              setError(
                "Não foi possível confirmar uma apresentação de alarme. Confira o histórico; a entrega não foi presumida.",
              );
          }
        }
      } catch {
        if (alive)
          setError(
            "Alarmes sem conexão com o servidor; nenhuma nova entrega foi confirmada.",
          );
      } finally {
        checking = false;
        if (refreshWanted && alive) {
          refreshWanted = false;
          void check();
        }
      }
    }
    void check();
    const timer = setInterval(check, 15000);
    const refresh = () => void check();
    window.addEventListener("online", refresh);
    window.addEventListener("saly-alarms-changed", refresh);
    return () => {
      alive = false;
      controller.abort();
      clearInterval(timer);
      window.removeEventListener("online", refresh);
      window.removeEventListener("saly-alarms-changed", refresh);
    };
  }, [enabled]);
  return (
    <>
      {error && <p role="status">{error}</p>}
      {items.map((item) => (
        <section
          className="notice"
          role="alert"
          aria-label="Ocorrência de alarme"
          key={item.id}
        >
          <div>
            <strong>{item.title}</strong>
            <p>{item.message}</p>
            <small>
              Alarme na interface. Som depende de permissão/interação; este
              aviso não comprova entrega por Push ou despertador nativo.
            </small>
            <div className="toolbar">
              <button
                onClick={async () => {
                  try {
                    await post(`/alarm-occurrences/${item.id}/dismiss`);
                    setItems((previous) =>
                      previous.filter((other) => other.id !== item.id),
                    );
                    stopAlarmAudio();
                    callbacks.current.stop();
                    window.dispatchEvent(new Event("saly-alarms-changed"));
                  } catch (error) {
                    setError((error as Error).message);
                  }
                }}
              >
                Concluir aviso
              </button>
              <button
                className="secondary"
                onClick={async () => {
                  try {
                    await post(`/alarm-occurrences/${item.id}/snooze`, {
                      minutes: item.snooze_minutes,
                    });
                    setItems((previous) =>
                      previous.filter((other) => other.id !== item.id),
                    );
                    stopAlarmAudio();
                    callbacks.current.stop();
                    window.dispatchEvent(new Event("saly-alarms-changed"));
                  } catch (error) {
                    setError((error as Error).message);
                  }
                }}
              >
                Adiar {item.snooze_minutes} min
              </button>
            </div>
          </div>
        </section>
      ))}
    </>
  );
}
