import { useState } from "react";
import { post } from "./api";

export function MemoryImport({
  notify,
  reload,
}: {
  notify: (message: string) => void;
  reload: () => Promise<unknown>;
}) {
  const [candidate, setCandidate] = useState<unknown>(null);
  const [preview, setPreview] = useState<{
    count: number;
    categories: string[];
    notice: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <>
      <label className="file-button">
        Importar JSON
        <input
          type="file"
          accept=".json,application/json"
          disabled={busy}
          onChange={async (event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (!file) return;
            setCandidate(null);
            setPreview(null);
            setBusy(true);
            try {
              if (file.size > 5_000_000)
                throw new Error("Máximo de 5 MB por arquivo JSON.");
              let data: unknown;
              try {
                data = JSON.parse(await file.text());
              } catch {
                throw new Error(
                  "JSON inválido: confira aspas, vírgulas e chaves do arquivo.",
                );
              }
              if (
                typeof data === "object" &&
                data !== null &&
                "arquivo" in data &&
                data.arquivo === "SALY_CORE_MEMORY_v1.json"
              ) {
                notify(
                  "Este arquivo é Core Memory, não uma lista de memórias. Abra Configurações → Sistema → Verificação administrativa do Core. A semente fornecida já está integrada ao backend.",
                );
                return;
              }
              const result = await post("/memories-import/preview", data);
              setCandidate(data);
              setPreview(result);
            } catch (error) {
              notify((error as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        />
      </label>
      {preview && (
        <section className="card" aria-label="Prévia da importação">
          <h3>Revisar importação</h3>
          <p>
            {preview.count} memórias · Categorias:{" "}
            {preview.categories.join(", ")}
          </p>
          <p>{preview.notice}</p>
          <button
            disabled={busy}
            onClick={async () => {
              if (
                !confirm(
                  `Autorizar a criação de ${preview.count} memórias a partir deste arquivo?`,
                )
              )
                return;
              setBusy(true);
              try {
                const result = await post("/memories-import", candidate);
                setPreview(null);
                setCandidate(null);
                await reload();
                notify(`${result.imported} memórias importadas.`);
              } catch (error) {
                notify((error as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            Confirmar importação
          </button>
          <button
            className="secondary"
            disabled={busy}
            onClick={() => {
              setPreview(null);
              setCandidate(null);
            }}
          >
            Cancelar importação
          </button>
        </section>
      )}
    </>
  );
}
