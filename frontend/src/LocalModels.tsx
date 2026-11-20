import { useEffect, useRef, useState } from "react";
import { api, post, put } from "./api";
const labels: Record<string, string> = {
  ready: "verificado",
  installed_unverified: "instalado, testar",
  not_installed: "não instalado",
  server_offline: "servidor desligado",
  resource_error: "memória insuficiente",
  communication_error: "falha na geração/comunicação",
};
type Model = { id: string; status: string; digest?: string };
type Catalog = { selected: string; default: string; models: Model[] };
export function LocalModels({
  conversation,
  busy = false,
  changed,
  pendingChanged,
}: {
  conversation?: string | null;
  busy?: boolean;
  changed?: () => Promise<void>;
  pendingChanged?: (pending: boolean) => void;
}) {
  const [data, setData] = useState<Catalog | null>(null),
    [pending, setPending] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const current = useRef(conversation);
  current.current = conversation;
  const sequence = useRef(0);
  async function refresh(signal?: AbortSignal) {
    if (conversation !== current.current) return;
    const scope = conversation,
      ticket = ++sequence.current;
    const next = (await api(
      "/local-models" +
        (scope ? "?conversation_id=" + encodeURIComponent(scope) : ""),
      { signal },
    )) as Catalog;
    if (
      !signal?.aborted &&
      scope === current.current &&
      ticket === sequence.current
    )
      setData(next);
  }
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError("");
    setNotice("");
    refresh(controller.signal).catch((e) => {
      if (!controller.signal.aborted) setError(e.message);
    });
    return () => {
      controller.abort();
      sequence.current++;
    };
  }, [conversation]);
  async function action(run: () => Promise<string>) {
    const scope = conversation;
    setPending(true);
    pendingChanged?.(true);
    setError("");
    setNotice("");
    try {
      const message = await run();
      if (scope === current.current) setNotice(message);
    } catch (e) {
      if (scope === current.current) setError((e as Error).message);
    } finally {
      // Also refresh after a failed generation: resource/connection failures are persisted.
      try {
        await refresh();
        await changed?.();
      } catch (e) {
        if (scope === current.current) setError((e as Error).message);
      }
      setPending(false);
      pendingChanged?.(false);
    }
  }
  const selected = data?.models.find((m) => m.id === data.selected);
  const local = !!data && data.selected !== "remote";
  const installed = !!selected?.digest;
  const locked = busy || pending;
  return (
    <section className="local-models" aria-label="Seleção de modelo">
      <label>
        Modelo da conversa
        <select
          aria-label="Modelo da conversa"
          disabled={locked || !data}
          value={data?.selected || "remote"}
          onChange={(e) => {
            const model = e.target.value;
            void action(async () => {
              await put("/local-models/selection", {
                model,
                conversation_id: conversation || null,
              });
              return conversation
                ? "Modelo alterado nesta conversa. Histórico preservado."
                : "Modelo padrão atualizado para novas conversas.";
            });
          }}
        >
          <option value="remote">Provedor remoto configurado</option>
          {data?.models
            .filter(
              (m) =>
                ["granite4:3b", "phi4-mini", data.selected].includes(m.id) ||
                m.digest,
            )
            .map((m) => (
              <option key={m.id} value={m.id}>
                {m.id} · {labels[m.status] || m.status}
              </option>
            ))}
        </select>
      </label>
      <small>
        {conversation
          ? "A escolha vale para a conversa aberta, inclusive em Configurações."
          : "Esta escolha será usada na próxima conversa."}
      </small>
      {pending && (
        <p className="model-status" role="status">
          Salvando ou verificando o modelo…
        </p>
      )}
      {!pending && notice && (
        <p className="model-status" role="status">
          {notice}
        </p>
      )}
      {busy && !pending && (
        <p>Aguarde a resposta terminar ou use Interromper antes de trocar.</p>
      )}
      {local && selected?.status !== "ready" && (
        <p className="model-availability">
          {selected?.status === "not_installed"
            ? "Selecionado, mas ainda não instalado no servidor. Execute bash scripts/setup-ollama.sh no terminal."
            : selected?.status === "server_offline"
              ? "Ollama está desligado. Execute bash scripts/start-ollama.sh no terminal e atualize a lista."
              : selected?.status === "installed_unverified"
                ? "Modelo instalado. Clique em Testar modelo local para verificar a geração e liberar o envio."
                : selected?.status === "resource_error"
                  ? "A geração falhou por falta de memória. Consulte os recursos do servidor antes de testar novamente."
                  : "Não foi possível confirmar a geração local. Atualize a lista e confira o servidor Ollama."}
        </p>
      )}
      {local && installed && selected?.status !== "ready" && (
        <button
          className="secondary"
          disabled={locked || !installed}
          onClick={() =>
            void action(async () => {
              const result = await post("/local-models/probe", {
                model: data!.selected,
              });
              return `Geração local verificada em ${result.seconds}s: ${result.response}`;
            })
          }
        >
          Testar modelo local
        </button>
      )}
      <details className="model-options">
        <summary>Opções de conexão e padrão</summary>
        <div className="toolbar">
          {local && selected?.status === "ready" && (
            <button
              className="secondary"
              disabled={locked || !installed}
              onClick={() =>
                void action(async () => {
                  const result = await post("/local-models/probe", {
                    model: data!.selected,
                  });
                  return `Geração local verificada em ${result.seconds}s: ${result.response}`;
                })
              }
            >
              Testar modelo local
            </button>
          )}
          <button
            className="text-button"
            disabled={locked}
            onClick={() =>
              void action(async () => "Lista de modelos atualizada.")
            }
          >
            Atualizar modelos
          </button>
          {conversation && data && data.selected !== data.default && (
            <button
              className="text-button"
              disabled={locked}
              onClick={() =>
                void action(async () => {
                  await put("/local-models/selection", {
                    model: data.selected,
                  });
                  return "Modelo escolhido também como padrão para novas conversas.";
                })
              }
            >
              Usar também como padrão
            </button>
          )}
        </div>
        {local && (
          <small>
            Execução no servidor. Ferramentas e visão locais ainda não
            verificadas.
          </small>
        )}
      </details>
      {error && <p role="alert">Não foi possível concluir: {error}</p>}
    </section>
  );
}
