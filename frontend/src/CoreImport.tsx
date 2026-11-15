import { useState } from "react";
import { post } from "./api";

type Preview = {
  id: string;
  digest: string;
  compatible: boolean;
  already_active: boolean;
  schema_version: string;
  rules: number;
  domains: number;
  notice: string;
};

export function CoreImport({ notify }: { notify: (message: string) => void }) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [backup, setBackup] = useState("");
  return (
    <section className="card" aria-label="Verificação administrativa do Core">
      <h2>Verificação administrativa do Core</h2>
      <p>
        Core Memory contém políticas e conhecimento de configuração. Memórias
        pessoais são importadas na aba Memórias. Novas políticas precisam de
        revisão no manifesto do projeto.
      </p>
      <label className="file-button">
        Selecionar JSON do Core
        <input
          type="file"
          accept=".json,application/json"
          disabled={busy}
          onChange={async (event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (!file) return;
            setPreview(null);
            setBackup("");
            setBusy(true);
            try {
              if (file.size > 500_000)
                throw new Error("Máximo de 500 KB para configuração Core.");
              let document: unknown;
              try {
                document = JSON.parse(await file.text());
              } catch {
                throw new Error(
                  "Arquivo JSON inválido. Confira aspas, vírgulas e chaves.",
                );
              }
              setPreview(await post("/core/preview", { document }));
            } catch (error) {
              notify((error as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        />
      </label>
      {preview && (
        <div>
          <p>
            Versão {preview.schema_version} · {preview.rules} regras ·{" "}
            {preview.domains} áreas
          </p>
          <p>{preview.notice}</p>
          {preview.already_active && (
            <p>
              Esta semente já está ativa. A confirmação cria um backup e
              registra a revisão; não adiciona memórias nem treina o modelo.
            </p>
          )}
          <button
            disabled={busy || !preview.compatible}
            onClick={async () => {
              if (
                !confirm(
                  "Criar backup privado e confirmar a revisão desta versão do Core?",
                )
              )
                return;
              setBusy(true);
              try {
                const result = await post(
                  `/core/imports/${preview.id}/confirm`,
                  { confirm: true, digest: preview.digest },
                );
                setBackup(result.backup_url);
                setPreview(null);
                notify(
                  "Backup criado e ativação do Core verificada. Nenhuma memória pessoal foi criada.",
                );
              } catch (error) {
                notify((error as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            Criar backup e confirmar revisão
          </button>
        </div>
      )}
      {backup && (
        <a className="citation" href={backup} download>
          Baixar backup privado do Core
        </a>
      )}
    </section>
  );
}
