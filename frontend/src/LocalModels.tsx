import { useEffect, useState } from "react";
import { api, post, put } from "./api";
const labels: Record<string, string> = {
  ready: "verificado",
  installed_unverified: "instalado, testar",
  not_installed: "não instalado",
  server_offline: "servidor desligado",
  resource_error: "memória insuficiente",
  communication_error: "falha na geração/comunicação",
};
export function LocalModels({
  conversation,
  busy = false,
  changed,
  notify,
}: {
  conversation?: string | null;
  busy?: boolean;
  changed?: () => void;
  notify: (s: string) => void;
}) {
  const [data, setData] = useState<any>(null),
    [testing, setTesting] = useState(false);
  const refresh = () =>
    api(
      "/local-models" +
        (conversation
          ? "?conversation_id=" + encodeURIComponent(conversation)
          : ""),
    ).then(setData);
  useEffect(() => {
    refresh().catch((e) => notify(e.message));
  }, [conversation]);
  return (
    <details className="local-models">
      <summary>
        Modelo da conversa{" "}
        {data?.selected &&
          `· ${data.selected === "remote" ? "provedor remoto" : data.selected}`}
      </summary>
      <label>
        Modelo {conversation ? "nesta conversa" : "padrão para novas conversas"}
        <select
          aria-label="Modelo da conversa"
          disabled={busy || testing || !data}
          value={data?.selected || "remote"}
          onChange={async (e) => {
            try {
              await put("/local-models/selection", {
                model: e.target.value,
                conversation_id: conversation || null,
              });
              await refresh();
              if (changed) changed();
              else window.dispatchEvent(new Event("saly-model-changed"));
            } catch (e) {
              notify((e as Error).message);
            }
          }}
        >
          <option value="remote">Provedor remoto configurado</option>
          {data?.models.map((m: any) => (
            <option key={m.id} value={m.id}>
              {m.id} · {labels[m.status] || m.status}
            </option>
          ))}
        </select>
      </label>
      {busy && (
        <small>
          Aguarde a resposta terminar ou use Interromper antes de trocar.
        </small>
      )}
      <button
        className="secondary"
        disabled={busy || testing}
        onClick={() => refresh().catch((e) => notify(e.message))}
      >
        Atualizar modelos
      </button>{" "}
      <button
        className="secondary"
        disabled={busy || testing || !data || data.selected === "remote"}
        onClick={async () => {
          setTesting(true);
          try {
            const r = await post("/local-models/probe", {
              model: data.selected,
            });
            notify(`Geração local: ${r.seconds}s · ${r.response}`);
            await refresh();
            if (changed) changed();
            else window.dispatchEvent(new Event("saly-model-changed"));
          } catch (e) {
            notify((e as Error).message);
          } finally {
            setTesting(false);
          }
        }}
      >
        {testing ? "Testando geração real…" : "Testar modelo local"}
      </button>
      <p>
        <small>
          Ollama executa no servidor, não no Android. Nenhum modelo é baixado
          automaticamente. Ferramentas e visão locais ainda não foram
          verificadas.
        </small>
      </p>
    </details>
  );
}
