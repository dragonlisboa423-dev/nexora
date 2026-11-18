import { useEffect, useState } from "react";
import { Leaf, Plus, ArrowUpRight, ImagePlus, PiggyBank } from "lucide-react";
import { api, post, put } from "./api";
import { money, cents, spendingSeries } from "./finance";
type Data = Record<string, any>;
const colors = [
  "#b9ce96",
  "#829f67",
  "#527b57",
  "#d3d5ab",
  "#6b8a72",
  "#a3b58e",
];
export function PurchaseOverview({
  summary,
  items,
  month,
}: {
  summary: Data;
  items: Data[];
  month: string;
}) {
  const categories = Object.entries(summary.categories) as [string, number][],
    total = summary.total_cents,
    budget = summary.budget_cents;
  let offset = 0;
  const segments = categories.map(([, value], i) => {
    const start = offset;
    offset += total ? (value / total) * 100 : 0;
    return `${colors[i % colors.length]} ${start}% ${offset}%`;
  });
  const series = spendingSeries(items, month),
    max = Math.max(1, ...series.map((s) => s.cents));
  return (
    <section
      className="purchase-overview"
      aria-label="Visão financeira dos registros"
    >
      <div className="financial-metrics">
        <article>
          <small>COMPRAS DO MÊS</small>
          <strong>{money(total)}</strong>
          <span>{summary.count} registros realizados</span>
        </article>
        <article>
          <small>ORÇAMENTO</small>
          <strong>{budget === null ? "A definir" : money(budget)}</strong>
          <span>
            {budget === null
              ? "Escolha um limite para o mês"
              : "Valor informado por você"}
          </span>
        </article>
        <article>
          <small>DISPONÍVEL NO ORÇAMENTO</small>
          <strong className={summary.remaining_cents < 0 ? "over-budget" : ""}>
            {summary.remaining_cents === null
              ? "—"
              : money(summary.remaining_cents)}
          </strong>
          <span>
            {summary.remaining_cents === null
              ? "Defina seu orçamento"
              : summary.remaining_cents < 0
                ? "Gastos registrados acima do limite"
                : "Orçamento menos gastos registrados"}
          </span>
        </article>
      </div>
      <div className="financial-charts">
        <article className="card category-chart">
          <div className="chart-heading">
            <h2>Para onde foi</h2>
            <span>Distribuição de gastos</span>
          </div>
          <div className="category-chart-body">
            <div
              className={`expense-donut ${!total ? "empty" : ""}`}
              style={{
                background: total
                  ? `conic-gradient(${segments.join(",")})`
                  : undefined,
              }}
              role="img"
              aria-label={
                total
                  ? `Distribuição dos gastos: ${categories.map(([c, v]) => `${c}, ${money(v)}`).join("; ")}`
                  : "Sem gastos registrados para distribuir"
              }
            >
              <div>
                <Leaf size={17} />
                <strong>{summary.count}</strong>
                <small>compras</small>
              </div>
            </div>
            <div className="category-legend">
              {categories.length ? (
                categories.map(([category, value], i) => (
                  <div key={category}>
                    <i style={{ background: colors[i % colors.length] }} />
                    <span>
                      {category}
                      <small>{money(value)}</small>
                    </span>
                    <b>{total ? ((value / total) * 100).toFixed(0) : 0}%</b>
                  </div>
                ))
              ) : (
                <p>Suas categorias aparecem aqui após a primeira compra.</p>
              )}
            </div>
          </div>
        </article>
        <article className="card spending-chart">
          <div className="chart-heading">
            <h2>No seu ritmo</h2>
            <span>Últimos seis meses registrados</span>
          </div>
          <div
            className="spending-bars"
            role="img"
            aria-label={series
              .map((s) => `${s.month}: ${money(s.cents)}`)
              .join("; ")}
          >
            {series.map((s) => (
              <div key={s.month}>
                <small>{money(s.cents)}</small>
                <span>
                  <i
                    style={{
                      height: `${s.cents ? Math.max(2, (s.cents / max) * 100) : 0}%`,
                    }}
                  />
                </span>
                <b>{s.label}</b>
              </div>
            ))}
          </div>
          <div className="budget-caption">
            <span>
              {budget === null
                ? "Um plano começa com um limite."
                : `${money(total)} de ${money(budget)} registrados`}
            </span>
            {budget !== null && (
              <progress
                aria-label="Uso do orçamento mensal"
                max={Math.max(1, budget)}
                value={Math.min(total, budget)}
              />
            )}
          </div>
        </article>
      </div>
    </section>
  );
}
export function SavingsGoals({ notify }: { notify: (s: string) => void }) {
  const [goals, setGoals] = useState<Data[]>([]),
    [draft, setDraft] = useState<Data | null>(null),
    [error, setError] = useState(""),
    [loaded, setLoaded] = useState(false),
    [busy, setBusy] = useState(false);
  const load = () =>
    api("/savings-goals")
      .then((data) => {
        setGoals(data);
        setLoaded(true);
        setError("");
      })
      .catch((e) => setError(e.message));
  useEffect(() => {
    void load();
  }, []);
  return (
    <section className="savings-section">
      <div className="section-heading">
        <div>
          <small>UM PASSO DE CADA VEZ</small>
          <h2>Planos que crescem.</h2>
        </div>
        <button
          className="secondary"
          onClick={() => setDraft({ title: "", target: "", saved: "0,00" })}
        >
          <Plus size={15} />
          Nova meta
        </button>
      </div>
      {error && <p role="status">{error}</p>}
      {draft && (
        <form
          className="card goal-form"
          onSubmit={async (e) => {
            e.preventDefault();
            if (
              !confirm(
                "Guardar esta meta e os valores que você informou? Não há movimentação bancária.",
              )
            )
              return;
            setBusy(true);
            try {
              const data = {
                title: draft.title,
                target_cents: cents(draft.target),
                saved_cents: cents(draft.saved),
                base_revision: draft.revision ?? 0,
                confirm: true,
              };
              await (draft.id
                ? put(`/savings-goals/${draft.id}`, data)
                : post("/savings-goals", data));
              setDraft(null);
              await load();
            } catch (e) {
              notify((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <h3>{draft.id ? "Atualizar meta" : "Uma nova meta"}</h3>
          <label>
            Nome da meta
            <input
              required
              maxLength={120}
              value={draft.title}
              onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            />
          </label>
          <div className="form-grid">
            <label>
              Valor da meta em reais
              <input
                required
                inputMode="decimal"
                value={draft.target}
                onChange={(e) => setDraft({ ...draft, target: e.target.value })}
              />
            </label>
            <label>
              Valor já reservado em reais
              <input
                required
                inputMode="decimal"
                value={draft.saved}
                onChange={(e) => setDraft({ ...draft, saved: e.target.value })}
              />
            </label>
          </div>
          <button disabled={busy}>Guardar meta</button>
          <button
            type="button"
            className="text-button"
            onClick={() => setDraft(null)}
          >
            Cancelar
          </button>
        </form>
      )}
      <div className="savings-grid">
        {goals.map((goal) => (
          <article className="card savings-card" key={goal.id}>
            <PiggyBank size={24} strokeWidth={1.3} />
            <h3>{goal.title}</h3>
            <div>
              <strong>{money(goal.saved_cents)}</strong>
              <span>de {money(goal.target_cents)}</span>
            </div>
            <progress
              aria-label={`Progresso da meta ${goal.title}`}
              max={goal.target_cents}
              value={Math.min(goal.saved_cents, goal.target_cents)}
            />
            <p>
              {Math.round((goal.saved_cents / goal.target_cents) * 100)}%
              reservado · valores manuais
            </p>
            <div className="toolbar">
              <button
                className="text-button"
                onClick={() =>
                  setDraft({
                    ...goal,
                    target: (goal.target_cents / 100).toFixed(2),
                    saved: (goal.saved_cents / 100).toFixed(2),
                  })
                }
              >
                Atualizar meta
              </button>
              <button
                className="text-button"
                onClick={async () => {
                  if (!confirm("Excluir esta meta de economia?")) return;
                  try {
                    await api(
                      `/savings-goals/${goal.id}?base_revision=${goal.revision}&confirm=true`,
                      { method: "DELETE" },
                    );
                    await load();
                  } catch (e) {
                    notify((e as Error).message);
                  }
                }}
              >
                Excluir meta
              </button>
            </div>
          </article>
        ))}
      </div>
      {loaded && !goals.length && !draft && (
        <div className="savings-empty">
          <PiggyBank size={29} strokeWidth={1} />
          <p>
            Uma viagem, um livro, um projeto.
            <br />
            Escolha algo que vale guardar.
          </p>
          <button
            className="text-button"
            onClick={() => setDraft({ title: "", target: "", saved: "0,00" })}
          >
            Criar minha primeira meta <ArrowUpRight size={14} />
          </button>
        </div>
      )}
    </section>
  );
}
export function ProductPhoto({
  item,
  saved,
  notify,
}: {
  item: Data;
  saved: () => void;
  notify: (s: string) => void;
}) {
  const [editing, setEditing] = useState(false),
    [file, setFile] = useState<File | null>(null),
    [preview, setPreview] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }
    const uri = URL.createObjectURL(file);
    setPreview(uri);
    return () => URL.revokeObjectURL(uri);
  }, [file]);
  return (
    <div className="product-photo">
      {item.product_image_id ? (
        <>
          <img
            loading="lazy"
            src={`/api/private-assets/${item.product_image_id}`}
            alt={`Foto de ${item.product}`}
          />
          <button
            className="photo-edit"
            onClick={() => setEditing(!editing)}
            aria-label={`Alterar foto de ${item.product}`}
          >
            <ImagePlus size={16} />
          </button>
        </>
      ) : (
        <button
          className="product-photo-empty"
          onClick={() => setEditing(!editing)}
          aria-label={`Adicionar foto de ${item.product}`}
        >
          <ImagePlus size={26} strokeWidth={1} />
          <span>Adicionar foto</span>
        </button>
      )}
      {editing && (
        <div className="photo-editor">
          <p>Foto privada do produto. O comprovante permanece separado.</p>
          <label>
            Foto de {item.product}
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
          {preview && <img src={preview} alt="Prévia da foto do produto" />}
          <div className="toolbar">
            <button
              disabled={!file || busy}
              onClick={async () => {
                if (!file) return;
                setBusy(true);
                try {
                  const form = new FormData();
                  form.set("file", file);
                  await api(
                    `/purchases/${item.id}/product-photo?base_revision=${item.revision}`,
                    { method: "POST", body: form },
                  );
                  setFile(null);
                  setEditing(false);
                  saved();
                } catch (e) {
                  notify((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Guardar foto do produto
            </button>
            <button
              className="text-button"
              onClick={() => {
                setEditing(false);
                setFile(null);
              }}
            >
              Fechar foto
            </button>
            {item.product_image_id && (
              <button
                className="text-button"
                disabled={busy}
                onClick={async () => {
                  if (
                    !confirm(
                      "Excluir apenas a foto do produto? O comprovante será preservado.",
                    )
                  )
                    return;
                  try {
                    await api(
                      `/purchases/${item.id}/product-photo?base_revision=${item.revision}&confirm=true`,
                      { method: "DELETE" },
                    );
                    setEditing(false);
                    saved();
                  } catch (e) {
                    notify((e as Error).message);
                  }
                }}
              >
                Excluir foto
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
