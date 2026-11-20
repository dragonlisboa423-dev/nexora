import { useState } from "react";
import { post } from "./api";

export function ModelConnection({ health }: { health: any }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  if (!health)
    return (
      <section className="card">
        <h2>Conexão do modelo</h2>
        <p>
          O estado da conexão ainda não foi confirmado. Use o seletor acima para
          escolher e verificar o modelo.
        </p>
      </section>
    );
  if (health?.provider === "ollama")
    return (
      <section className="card">
        <h2>Modelo local</h2>
        <p>
          {health.model} · {health.detail}
        </p>
        <p>
          O chat usa o Core, as memórias autorizadas e os trechos do Centro
          Smolin. Chamadas de ferramentas e visão locais ainda não foram
          verificadas.
        </p>
      </section>
    );
  return (
    <section className="card">
      <small>MODELO + AGENTE SALY</small>
      <h2>Uma conexão para toda a assistente</h2>
      <p>
        Chat, memória, Centro Smolin, agenda e ferramentas usam o mesmo modelo,
        respeitando suas permissões.
      </p>
      <p>
        O agente está incluído no projeto, sem assinatura própria. As chamadas
        usam a cota da sua conta no provedor.
      </p>
      <div className="tags">
        <span>Memória</span>
        <span>Centro Smolin</span>
        <span>Agenda</span>
        <span>Ferramentas com aprovação</span>
      </div>
      {!health?.configured && (
        <p>
          Para ativar, execute <code>bash scripts/connect-model.sh</code> no
          terminal privado do servidor. Não insira chaves no chat.
        </p>
      )}
      <p>
        {health?.agent?.tools_available ?? 0} ferramentas configuradas ·{" "}
        {health?.model || "modelo não verificado"}
      </p>
      <button
        disabled={busy || !health?.model_ready}
        onClick={async () => {
          setBusy(true);
          setError("");
          setResult(null);
          try {
            setResult(await post("/system/test-connection"));
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Verificando modelo e ferramenta…" : "Testar conexão e agente"}
      </button>
      <small>
        O teste usa duas chamadas curtas da sua cota, sem enviar memórias ou
        documentos.
      </small>
      {result && (
        <p role="status">
          Conexão verificada: streaming, chamada de ferramenta e resultado{" "}
          {result.tool_result}. Modelo: {result.model}.
        </p>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
