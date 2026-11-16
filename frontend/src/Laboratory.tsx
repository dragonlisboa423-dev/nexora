import { useEffect, useState } from "react";
import { deviceChecks } from "./device_lab";
import { api, download, post } from "./api";

type Core = {
  schema_version: string;
  adapter_version: string;
  sha256: string;
  rules: number;
  domains: number;
  package_status: string;
};
type Result = {
  id: string;
  category: string;
  status: "passed" | "failed" | "inconclusive";
  input: unknown;
  expected: unknown;
  observed: unknown;
  evidence: string;
  duration_ms: number;
};
type Run = {
  id: string;
  timestamp: string;
  app_version: string;
  rules_version: string;
  core_sha256: string;
  model_version: string;
  duration_ms: number;
  provider_requests: number;
  summary: Partial<Record<Result["status"], number>>;
  scope: string;
  results: Result[];
  capabilities: { id: string; name: string; state: string; detail: string }[];
};
const statuses = {
  passed: "Passou",
  failed: "Falhou",
  inconclusive: "Inconclusivo · teste ou dependência pendente",
};
const capabilityStates: Record<string, string> = {
  configured: "Configurado · requer teste específico",
  partial: "Parcialmente implementado",
  blocked: "Pendente / bloqueado",
};
const show = (value: unknown) =>
  typeof value === "string" ? value : JSON.stringify(value, null, 2);

export function Laboratory({ notify }: { notify: (message: string) => void }) {
  const [core, setCore] = useState<Core | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    Promise.all([api("/core"), api("/laboratory")])
      .then(([metadata, history]) => {
        setCore(metadata);
        setRuns(history);
      })
      .catch((error) => notify(error.message));
  }, []);
  return (
    <section aria-label="Laboratório SALY" className="card">
      <h2>Laboratório SALY</h2>
      <p>
        Verificações locais de regras, unidades e banco. Executar estes testes
        não chama o provedor de IA nem consome quota de API. Os 16 casos de
        linguagem ficam inconclusivos até uma avaliação específica do modelo.
      </p>
      {core && (
        <details>
          <summary>
            Core {core.schema_version} · {core.rules} regras · {core.domains}{" "}
            áreas
          </summary>
          <p>
            Adaptador {core.adapter_version} · SHA-256 {core.sha256}
          </p>
          <p>{core.package_status}</p>
        </details>
      )}
      <button
        disabled={busy || !core}
        onClick={async () => {
          setBusy(true);
          try {
            const report = await post("/laboratory");
            setRuns((previous) => [report, ...previous].slice(0, 50));
          } catch (error) {
            notify((error as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Verificando localmente…" : "Executar testes locais · sem API"}
      </button>
      <div className="toolbar">
        <button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              const report = await post("/laboratory/features");
              setRuns((previous) => [report, ...previous].slice(0, 50));
            } catch (e) {
              notify((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          Testar recursos locais · sem API externa
        </button>
        <button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              const report = await post("/laboratory/device", {
                results: await deviceChecks(),
              });
              setRuns((previous) => [report, ...previous].slice(0, 50));
            } catch (e) {
              notify((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          Testar este dispositivo · som curto
        </button>
      </div>
      <p>
        Diagnóstico funcional usa entradas técnicas fixas para agenda, centavos,
        URLs, livro, PNG, PDF, WAV e codec MP4. Não dispara seus alarmes nem
        acessa documentos pessoais. Teste do dispositivo verifica PCM, IndexedDB
        e cache público no navegador atual.
      </p>
      {runs.map((run) => (
        <article
          key={run.id}
          className="card"
          aria-label="Relatório do laboratório"
        >
          <h3>{new Date(run.timestamp).toLocaleString("pt-BR")}</h3>
          <p role="status">
            {run.summary.passed ?? 0} passaram · {run.summary.failed ?? 0}{" "}
            falharam
            {" · "}
            {run.summary.inconclusive ?? 0} inconclusivos
          </p>
          <p>
            App {run.app_version} · Core {run.rules_version} · {run.duration_ms}{" "}
            ms
            {" · "}
            {run.provider_requests} chamadas ao provedor
          </p>
          <small>
            Modelo configurado: {run.model_version} · não avaliado nesta
            execução
          </small>
          <p>{run.scope}</p>
          <button
            className="secondary"
            onClick={() => download(`saly-lab-${run.id}.json`, run)}
          >
            Exportar relatório JSON
          </button>
          <details>
            <summary>Disponibilidade de cada recurso</summary>
            {run.capabilities.map((item) => (
              <div key={item.id}>
                <h4>
                  {item.name} · {capabilityStates[item.state] ?? item.state}
                </h4>
                <p>{item.detail}</p>
              </div>
            ))}
          </details>
          <details>
            <summary>
              Entradas, resultados e evidências ({run.results.length} casos)
            </summary>
            {run.results.map((result) => (
              <details key={result.id}>
                <summary>
                  {result.id} · {result.category} · {statuses[result.status]}
                </summary>
                <p>Entrada</p>
                <pre className="tool-result">{show(result.input)}</pre>
                <p>Esperado</p>
                <pre className="tool-result">{show(result.expected)}</pre>
                <p>Observado</p>
                <pre className="tool-result">{show(result.observed)}</pre>
                <p>
                  {result.evidence} · {result.duration_ms} ms
                </p>
              </details>
            ))}
          </details>
        </article>
      ))}
    </section>
  );
}

export type Verification = {
  scope: string;
  core?: { schema_version: string; sha256: string; principle_ids: string[] };
  tools?: {
    tool: string;
    executed: boolean;
    execution_id: string | null;
    approval_id: string | null;
    deterministic_result?: unknown;
  }[];
};

export function VerificationDetails({
  verification,
}: {
  verification: Verification;
}) {
  return (
    <details className="sources">
      <summary>Evidências e verificações da resposta</summary>
      <p>{verification.scope}</p>
      <p>
        Registro no momento da resposta. Consulte aprovações posteriores em
        Ferramentas e integrações.
      </p>
      {verification.core && (
        <>
          <p>
            Core {verification.core.schema_version} · SHA-256{" "}
            {verification.core.sha256}
          </p>
          <p>
            Princípios recuperados:{" "}
            {verification.core.principle_ids.join(", ") || "nenhum"}
          </p>
        </>
      )}
      {verification.tools?.map((tool, index) => (
        <div key={index}>
          <p>
            {tool.tool} ·{" "}
            {tool.executed ? "Execução confirmada" : "Não executada"}
          </p>
          <small>
            Registro: {tool.execution_id ?? "sem execução registrada"}
          </small>
          {tool.approval_id && <p>Proposta de aprovação: {tool.approval_id}</p>}
          {tool.deterministic_result !== undefined && (
            <pre className="tool-result">{show(tool.deterministic_result)}</pre>
          )}
        </div>
      ))}
    </details>
  );
}
