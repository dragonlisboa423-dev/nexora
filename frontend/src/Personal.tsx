import { useEffect, useState } from "react";
import { api, post, put, download } from "./api";
import { PageTitle } from "./Panels";

import { money, cents } from "./finance";
export { money, cents } from "./finance";
import {
  PurchaseOverview,
  SavingsGoals,
  ProductPhoto,
} from "./PurchaseDashboard";
type Data = Record<string, any>;
const statuses: Record<string, string> = {
  purchased: "Realizada",
  awaiting: "Aguardando entrega",
  delivered: "Entregue",
  wishlist: "Lista de desejos",
  planned: "Planejada",
  cancelled: "Cancelada",
};
export const purchaseFields = [
  "product",
  "price_cents",
  "quantity",
  "store_name",
  "purchased_on",
  "category",
  "shipping_cents",
  "discount_cents",
  "payment_method",
  "installments",
  "status",
  "expected_on",
  "received_on",
  "warranty_until",
  "return_until",
  "notes",
];
export const drawerFields = ["name", "color", "icon", "position"];
export const linkFields = [
  "title",
  "url",
  "description",
  "drawer_id",
  "tags",
  "position",
  "favorite",
  "allow_http",
];
const fields = (value: Data, keys: string[]) =>
  Object.fromEntries(keys.map((k) => [k, value[k]]));
const today = () => new Date().toLocaleDateString("sv-SE");
export const emptyPurchase = (): Data => ({
  product: "",
  price_cents: 0,
  quantity: 1,
  store_name: "",
  purchased_on: today(),
  category: "outros",
  shipping_cents: 0,
  discount_cents: 0,
  payment_method: "",
  installments: null,
  status: "purchased",
  expected_on: null,
  received_on: null,
  warranty_until: null,
  return_until: null,
  notes: "",
});
export const emptyDrawer = (): Data => ({
  name: "",
  color: "#7acfc1",
  icon: "folder",
  position: 0,
});
export const emptyLink = (drawer_id: string): Data => ({
  title: "",
  url: "https://",
  description: "",
  drawer_id,
  tags: [],
  position: 0,
  favorite: false,
  allow_http: false,
});

function MoneyInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  const [text, setText] = useState((value / 100).toFixed(2));
  return (
    <label>
      {label}
      <input
        required
        inputMode="decimal"
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          try {
            onChange(cents(e.target.value));
            e.target.setCustomValidity("");
          } catch (error) {
            e.target.setCustomValidity((error as Error).message);
          }
        }}
      />
    </label>
  );
}
function Receipt({
  item,
  saved,
  notify,
}: {
  item: Data;
  saved: () => void;
  notify: (s: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null),
    [preview, setPreview] = useState("");
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
    <details className="card">
      <summary>Comprovante privado · {item.product}</summary>
      <p>
        Cadastro manual. A SALY não lê nem presume valores da imagem. PNG, JPEG
        ou WebP estático; até 8 MB/16 MP. Metadados são removidos.
      </p>
      {item.image_id && (
        <>
          <a
            href={`/api/private-assets/${item.image_id}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Abrir comprovante
          </a>
          <img
            className="receipt-preview"
            src={`/api/private-assets/${item.image_id}`}
            alt={`Comprovante de ${item.product}`}
          />
          <button
            type="button"
            onClick={async () => {
              if (!confirm("Excluir este comprovante?")) return;
              try {
                await api(
                  `/purchases/${item.id}/image?confirm=true&base_revision=${item.revision}`,
                  { method: "DELETE" },
                );
                saved();
              } catch (e) {
                notify((e as Error).message);
              }
            }}
          >
            Excluir imagem
          </button>
        </>
      )}
      <label>
        Selecionar comprovante
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </label>
      {preview && (
        <img
          className="receipt-preview"
          src={preview}
          alt="Prévia do arquivo selecionado"
        />
      )}
      <button
        disabled={!file}
        onClick={async () => {
          if (
            !file ||
            !confirm("Guardar ou substituir este comprovante privado?")
          )
            return;
          const form = new FormData();
          form.set("file", file);
          try {
            await api(
              `/purchases/${item.id}/image?base_revision=${item.revision}`,
              { method: "POST", body: form },
            );
            setFile(null);
            saved();
          } catch (e) {
            notify((e as Error).message);
          }
        }}
      >
        Guardar imagem
      </button>
    </details>
  );
}
function PurchaseAlerts({
  item,
  saved,
  notify,
}: {
  item: Data;
  saved: () => void;
  notify: (s: string) => void;
}) {
  const [field, setField] = useState("expected_on"),
    [days, setDays] = useState(1),
    [zone, setZone] = useState("America/Sao_Paulo");
  return (
    <details>
      <summary>Alertas de entrega, garantia e devolução</summary>
      <p>
        Datas e status são manuais. O alarme é uma cópia da data; reveja-o em
        Alarmes se a compra mudar. Requer servidor e interface ativos.
      </p>
      <label>
        Data do alerta
        <select value={field} onChange={(e) => setField(e.target.value)}>
          <option value="expected_on">Entrega prevista</option>
          <option value="warranty_until">Fim da garantia</option>
          <option value="return_until">Fim da devolução</option>
        </select>
      </label>
      <label>
        Dias antes
        <input
          type="number"
          min="0"
          max="365"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        />
      </label>
      <label>
        Fuso do alerta
        <input value={zone} onChange={(e) => setZone(e.target.value)} />
      </label>
      <button
        onClick={async () => {
          if (!confirm("Criar alarme às 09:00 no fuso informado?")) return;
          try {
            await post(`/purchases/${item.id}/alarm`, {
              field,
              days_before: days,
              timezone: zone,
              local_time: "09:00",
              base_revision: item.revision,
              confirm: true,
            });
            window.dispatchEvent(new Event("saly-alarms-changed"));
            saved();
          } catch (e) {
            notify((e as Error).message);
          }
        }}
      >
        Criar alarme da compra
      </button>
    </details>
  );
}
export function Purchases({ notify }: { notify: (s: string) => void }) {
  const [items, setItems] = useState<Data[]>([]),
    [summary, setSummary] = useState<Data | null>(null),
    [month, setMonth] = useState(today().slice(0, 7)),
    [query, setQuery] = useState(""),
    [status, setStatus] = useState(""),
    [categoryFilter, setCategoryFilter] = useState(""),
    [draft, setDraft] = useState<Data | null>(null),
    [preview, setPreview] = useState<Data | null>(null),
    [busy, setBusy] = useState(false),
    [budget, setBudget] = useState("0,00");
  async function load() {
    const [rows, totals] = await Promise.all([
      api("/purchases"),
      api("/purchases-summary?month=" + month),
    ]);
    setItems(rows);
    setSummary(totals);
    setBudget(((totals.budget_cents ?? 0) / 100).toFixed(2));
  }
  useEffect(() => {
    let alive = true;
    Promise.all([api("/purchases"), api("/purchases-summary?month=" + month)])
      .then(([rows, totals]) => {
        if (alive) {
          setItems(rows);
          setSummary(totals);
          setBudget(((totals.budget_cents ?? 0) / 100).toFixed(2));
        }
      })
      .catch((e) => notify(e.message));
    return () => {
      alive = false;
    };
  }, [month]);
  function change(key: string, value: any) {
    setDraft((d) => (d ? { ...d, [key]: value } : d));
    setPreview(null);
  }
  const filtered = items.filter(
    (p) =>
      (!status || p.status === status) &&
      (!categoryFilter || p.category === categoryFilter) &&
      `${p.product} ${p.store_name} ${p.category}`
        .toLocaleLowerCase()
        .includes(query.toLocaleLowerCase()) &&
      ((!p.purchased_on && ["wishlist", "planned"].includes(p.status)) ||
        p.purchased_on?.startsWith(month)),
  );
  return (
    <>
      <PageTitle
        eyebrow="ROTINA · COMPRAS E DESEJOS"
        title="Compras"
        text="O que você deseja. O que já chegou. E espaço para seus próximos planos."
      />
      {summary && (
        <PurchaseOverview summary={summary} items={items} month={month} />
      )}
      <SavingsGoals notify={notify} />
      <div className="section-heading">
        <div>
          <small>SUAS ESCOLHAS</small>
          <h2>Compras e desejos</h2>
        </div>
      </div>
      <div className="toolbar purchase-filters">
        <label>
          Período das compras
          <input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
          />
        </label>
        <label>
          Pesquisar compras
          <input value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        <label>
          Status da compra
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todas as listas</option>
            {Object.entries(statuses).map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label>
          Categoria de compras
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="">Todas as categorias</option>
            {[...new Set(items.map((p) => p.category))].sort().map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <button
          onClick={() => {
            setDraft(emptyPurchase());
            setPreview(null);
          }}
        >
          + Nova compra
        </button>
        <button
          onClick={() =>
            api("/personal-export")
              .then((data) => download("saly-compras.json", data))
              .catch((e) => notify(e.message))
          }
        >
          Exportar registros
        </button>
      </div>
      {summary && (
        <details className="card purchase-budget-settings">
          <summary>Orçamento e detalhes do mês</summary>
          <h2>Resumo de {month}</h2>
          <div className="stats">
            <span>
              Gastos: <strong>{money(summary.total_cents)}</strong>
            </span>
            <span>Compras: {summary.count}</span>
            <span>
              Saldo:{" "}
              {summary.remaining_cents === null
                ? "Orçamento não definido"
                : money(summary.remaining_cents)}
            </span>
          </div>
          <form
            className="toolbar"
            onSubmit={async (e) => {
              e.preventDefault();
              if (!confirm("Salvar orçamento mensal?")) return;
              try {
                await put("/purchases-budget", {
                  month,
                  amount_cents: cents(budget),
                  confirm: true,
                });
                await load();
              } catch (e) {
                notify((e as Error).message);
              }
            }}
          >
            <label>
              Orçamento em reais
              <input
                inputMode="decimal"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                required
              />
            </label>
            <button>Salvar orçamento</button>
          </form>
          <h3>Gastos por categoria</h3>
          {Object.entries(summary.categories).map(([category, amount]) => (
            <div key={category} className="budget-bar">
              <span>
                {category} · {money(amount as number)}
              </span>
              <meter
                aria-label={`Gastos em ${category}`}
                min="0"
                max={Math.max(1, summary.total_cents)}
                value={amount as number}
              />
            </div>
          ))}
          {!summary.count && (
            <p>
              Sem gastos realizados neste mês. Desejos e planejamentos não
              entram no total.
            </p>
          )}
          <details>
            <summary>Parcelas informadas</summary>
            <p>
              Divisão aritmética do valor cadastrado, sem juros, vencimentos ou
              cobrança automática.
            </p>
            {summary.installments.map((p: Data) => (
              <p key={p.id}>
                {p.product}: {p.count} parcelas de base {money(p.base_cents)};
                distribuir {p.remainder_cents} centavo(s) restante(s).
              </p>
            ))}
          </details>
        </details>
      )}
      {draft && (
        <section className="card" role="region" aria-label="Editor de compra">
          <h2>{draft.id ? "Editar compra" : "Cadastrar compra"}</h2>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              try {
                setPreview(
                  await post(
                    "/purchases/preview",
                    fields(draft, purchaseFields),
                  ),
                );
              } catch (e) {
                notify((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <div className="form-grid">
              <label>
                Produto
                <input
                  required
                  maxLength={300}
                  value={draft.product}
                  onChange={(e) => change("product", e.target.value)}
                />
              </label>
              <MoneyInput
                key={`price-${draft.id}`}
                label="Preço unitário em reais"
                value={draft.price_cents}
                onChange={(v) => change("price_cents", v)}
              />
              <label>
                Quantidade
                <input
                  type="number"
                  min="1"
                  max="10000"
                  required
                  value={draft.quantity}
                  onChange={(e) => change("quantity", Number(e.target.value))}
                />
              </label>
              <MoneyInput
                key={`shipping-${draft.id}`}
                label="Frete em reais"
                value={draft.shipping_cents}
                onChange={(v) => change("shipping_cents", v)}
              />
              <MoneyInput
                key={`discount-${draft.id}`}
                label="Desconto em reais"
                value={draft.discount_cents}
                onChange={(v) => change("discount_cents", v)}
              />
              {[
                ["store_name", "Loja"],
                ["category", "Categoria"],
                ["payment_method", "Forma de pagamento"],
              ].map(([key, label]) => (
                <label key={key}>
                  {label}
                  <input
                    value={draft[key]}
                    onChange={(e) => change(key, e.target.value)}
                  />
                </label>
              ))}
              <label>
                Estado manual
                <select
                  value={draft.status}
                  onChange={(e) => change("status", e.target.value)}
                >
                  {Object.entries(statuses).map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Parcelas opcionais
                <input
                  type="number"
                  min="1"
                  max="120"
                  value={draft.installments ?? ""}
                  onChange={(e) =>
                    change(
                      "installments",
                      e.target.value ? Number(e.target.value) : null,
                    )
                  }
                />
              </label>
              {[
                ["purchased_on", "Data da compra"],
                ["expected_on", "Entrega prevista"],
                ["received_on", "Recebida em"],
                ["warranty_until", "Garantia até"],
                ["return_until", "Devolução até"],
              ].map(([key, label]) => (
                <label key={key}>
                  {label}
                  <input
                    type="date"
                    value={draft[key] ?? ""}
                    onChange={(e) => change(key, e.target.value || null)}
                  />
                </label>
              ))}
            </div>
            <label>
              Observações da compra
              <textarea
                maxLength={5000}
                value={draft.notes}
                onChange={(e) => change("notes", e.target.value)}
              />
            </label>
            <div className="toolbar">
              <button disabled={busy}>Conferir total</button>
              <button
                type="button"
                onClick={() => {
                  setDraft(null);
                  setPreview(null);
                }}
              >
                Fechar editor
              </button>
            </div>
          </form>
          {preview && (
            <div role="region" aria-label="Total conferido">
              <p>
                Total: <strong>{money(preview.total_cents)}</strong>
              </p>
              <button
                disabled={busy}
                onClick={async () => {
                  if (!confirm("Salvar os dados manuais desta compra?")) return;
                  setBusy(true);
                  try {
                    await api("/purchases" + (draft.id ? "/" + draft.id : ""), {
                      method: draft.id ? "PATCH" : "POST",
                      body: JSON.stringify({
                        data: fields(draft, purchaseFields),
                        base_revision: draft.revision,
                        confirm: true,
                      }),
                    });
                    setDraft(null);
                    setPreview(null);
                    await load();
                  } catch (e) {
                    notify((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Confirmar compra
              </button>
            </div>
          )}
        </section>
      )}
      <div className="personal-grid product-grid">
        {filtered.map((item) => (
          <article className="card product-card" key={item.id}>
            <ProductPhoto
              item={item}
              saved={() => load().catch((e) => notify(e.message))}
              notify={notify}
            />
            <div className="product-card-copy">
              <h2>{item.product}</h2>
              <p>
                {statuses[item.status]} · {item.category}
              </p>
              <strong>{money(item.total_cents)}</strong>
              <p>
                {item.quantity} unidade(s) · {item.store_name} ·{" "}
                {item.purchased_on ?? "Sem compra realizada"}
              </p>
              <p>{item.notes}</p>
              <div className="toolbar">
                <button
                  onClick={() => {
                    setDraft(item);
                    setPreview(null);
                  }}
                >
                  Editar {item.product}
                </button>
                <button
                  onClick={async () => {
                    if (
                      !confirm(
                        "Excluir compra, imagem privada e cancelar seus alarmes?",
                      )
                    )
                      return;
                    try {
                      await api(
                        `/purchases/${item.id}?confirm=true&base_revision=${item.revision}`,
                        { method: "DELETE" },
                      );
                      await load();
                    } catch (e) {
                      notify((e as Error).message);
                    }
                  }}
                >
                  Excluir {item.product}
                </button>
              </div>
              <Receipt
                key={item.id}
                item={item}
                saved={() => load().catch((e) => notify(e.message))}
                notify={notify}
              />
              <PurchaseAlerts
                item={item}
                saved={() => load().catch((e) => notify(e.message))}
                notify={notify}
              />
            </div>
          </article>
        ))}
      </div>
      {!filtered.length && (
        <div className="purchase-empty">
          <h3>
            {items.length
              ? "Nada nesta seleção."
              : "Cada escolha tem seu tempo."}
          </h3>
          <p>
            {items.length
              ? "Experimente outro período ou categoria."
              : "Adicione sua primeira compra ou desejo. Depois, escolha uma foto para reconhecê-lo de relance."}
          </p>
          <button
            className="secondary"
            onClick={() => {
              setDraft(emptyPurchase());
              setPreview(null);
            }}
          >
            Adicionar um item
          </button>
        </div>
      )}
      <p>
        Registros e valores são informados por você. O cofre local permite
        escolher compras para consulta offline; fotos e metas não são copiadas
        automaticamente.
      </p>
    </>
  );
}

export function Space({ notify }: { notify: (s: string) => void }) {
  const [drawers, setDrawers] = useState<Data[]>([]),
    [links, setLinks] = useState<Data[]>([]),
    [query, setQuery] = useState(""),
    [favorite, setFavorite] = useState(false),
    [draft, setDraft] = useState<Data | null>(null),
    [kind, setKind] = useState("drawers"),
    [busy, setBusy] = useState(false);
  async function load() {
    const [d, l] = await Promise.all([api("/drawers"), api("/links")]);
    setDrawers(
      d.sort(
        (a: Data, b: Data) =>
          a.position - b.position || a.name.localeCompare(b.name),
      ),
    );
    setLinks(l);
  }
  useEffect(() => {
    load().catch((e) => notify(e.message));
  }, []);
  async function save(data: Data, resource: string) {
    return api(`/${resource}` + (data.id ? `/${data.id}` : ""), {
      method: data.id ? "PATCH" : "POST",
      body: JSON.stringify({
        data: fields(data, resource === "drawers" ? drawerFields : linkFields),
        base_revision: data.revision,
        confirm: true,
      }),
    });
  }
  function edit(data: Data, resource: string) {
    setKind(resource);
    setDraft(data);
  }
  async function remove(item: Data, resource: string) {
    if (
      !confirm(
        resource === "drawers"
          ? "Excluir gaveta e todos os links dentro dela?"
          : "Excluir link?",
      )
    )
      return;
    try {
      await api(
        `/${resource}/${item.id}?confirm=true&base_revision=${item.revision}`,
        { method: "DELETE" },
      );
      await load();
    } catch (e) {
      notify((e as Error).message);
    }
  }
  const icons: Record<string, string> = {
    folder: "▣",
    book: "▤",
    star: "☆",
    science: "⚛",
    home: "⌂",
  };
  return (
    <>
      <PageTitle
        eyebrow="SEUS RECURSOS"
        title="Espaço"
        text="Gavetas digitais para seus recursos. Links são adicionados manualmente e não são visitados automaticamente."
      />
      <div className="toolbar">
        <label>
          Pesquisar links e etiquetas
          <input value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        <label>
          <input
            type="checkbox"
            checked={favorite}
            onChange={(e) => setFavorite(e.target.checked)}
          />
          Somente favoritos
        </label>
        <button
          onClick={() =>
            edit({ ...emptyDrawer(), position: drawers.length }, "drawers")
          }
        >
          + Nova gaveta
        </button>
        <button
          onClick={() =>
            download("saly-espaco.json", {
              format: "saly-space-v1",
              drawers,
              links,
            })
          }
        >
          Exportar Espaço
        </button>
        <label>
          Importar Espaço
          <input
            type="file"
            accept="application/json,.json"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (
                !file ||
                !confirm(
                  "Importar gavetas e links com novos IDs, preservando os atuais?",
                )
              )
                return;
              try {
                if (file.size > 4 * 1024 * 1024)
                  throw new Error("Arquivo acima de 4 MB.");
                const data = JSON.parse(await file.text());
                await post("/space-import", { ...data, confirm: true });
                await load();
              } catch (e) {
                notify((e as Error).message);
              }
            }}
          />
        </label>
      </div>
      {draft && (
        <section className="card" aria-label="Editor do Espaço">
          <h2>{kind === "drawers" ? "Editar gaveta" : "Editar link"}</h2>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (!confirm("Salvar este registro?")) return;
              setBusy(true);
              try {
                if (kind === "links")
                  await post("/links/preview", fields(draft, linkFields));
                await save(draft, kind);
                setDraft(null);
                await load();
              } catch (e) {
                notify((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              {kind === "drawers" ? "Nome da gaveta" : "Título do link"}
              <input
                required
                maxLength={kind === "drawers" ? 150 : 300}
                value={draft[kind === "drawers" ? "name" : "title"]}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    [kind === "drawers" ? "name" : "title"]: e.target.value,
                  })
                }
              />
            </label>
            {kind === "drawers" ? (
              <div className="form-grid">
                <label>
                  Cor da gaveta
                  <input
                    type="color"
                    value={draft.color}
                    onChange={(e) =>
                      setDraft({ ...draft, color: e.target.value })
                    }
                  />
                </label>
                <label>
                  Ícone
                  <select
                    value={draft.icon}
                    onChange={(e) =>
                      setDraft({ ...draft, icon: e.target.value })
                    }
                  >
                    {Object.entries(icons).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            ) : (
              <>
                <label>
                  URL do link
                  <input
                    required
                    type="url"
                    value={draft.url}
                    onChange={(e) =>
                      setDraft({ ...draft, url: e.target.value })
                    }
                  />
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={draft.allow_http}
                    onChange={(e) =>
                      setDraft({ ...draft, allow_http: e.target.checked })
                    }
                  />
                  Permitir HTTP sem criptografia para este link
                </label>
                <label>
                  Descrição do link
                  <textarea
                    value={draft.description}
                    onChange={(e) =>
                      setDraft({ ...draft, description: e.target.value })
                    }
                  />
                </label>
                <label>
                  Gaveta do link
                  <select
                    value={draft.drawer_id}
                    onChange={(e) =>
                      setDraft({ ...draft, drawer_id: e.target.value })
                    }
                  >
                    {drawers.map((d) => (
                      <option value={d.id} key={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Etiquetas separadas por vírgula
                  <input
                    value={draft.tags.join(",")}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        tags: e.target.value
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean),
                      })
                    }
                  />
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={draft.favorite}
                    onChange={(e) =>
                      setDraft({ ...draft, favorite: e.target.checked })
                    }
                  />
                  Favorito
                </label>
              </>
            )}
            <label>
              Posição
              <input
                type="number"
                min="0"
                max="100000"
                value={draft.position}
                onChange={(e) =>
                  setDraft({ ...draft, position: Number(e.target.value) })
                }
              />
            </label>
            <div className="toolbar">
              <button disabled={busy}>
                Salvar {kind === "drawers" ? "gaveta" : "link"}
              </button>
              <button type="button" onClick={() => setDraft(null)}>
                Fechar editor
              </button>
            </div>
          </form>
        </section>
      )}
      <div className="drawers">
        {drawers.map((drawer) => {
          const selected = links
            .filter(
              (l) =>
                l.drawer_id === drawer.id &&
                (!favorite || l.favorite) &&
                `${l.title} ${l.description} ${l.tags.join(" ")}`
                  .toLocaleLowerCase()
                  .includes(query.toLocaleLowerCase()),
            )
            .sort(
              (a, b) =>
                a.position - b.position || a.title.localeCompare(b.title),
            );
          return (
            <details
              className="drawer card"
              key={drawer.id}
              style={{ borderTopColor: drawer.color }}
              open={Boolean(query) || undefined}
            >
              <summary>
                {icons[drawer.icon]} {drawer.name} · {selected.length}
              </summary>
              <div className="toolbar">
                <button onClick={() => edit(drawer, "drawers")}>
                  Configurar {drawer.name}
                </button>
                <button onClick={() => edit(emptyLink(drawer.id), "links")}>
                  Adicionar link a {drawer.name}
                </button>
                <button onClick={() => remove(drawer, "drawers")}>
                  Excluir gaveta {drawer.name}
                </button>
              </div>
              <div className="personal-grid">
                {selected.map((link) => (
                  <article className="link-card" key={link.id}>
                    <h3>
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        referrerPolicy="no-referrer"
                      >
                        {link.title}
                      </a>
                    </h3>
                    <p className="url-text">{link.url}</p>
                    <p>{link.description}</p>
                    <small>{link.tags.join(" · ")}</small>
                    <div className="toolbar">
                      <button
                        aria-label={`Favoritar ${link.title}`}
                        onClick={async () => {
                          try {
                            await save(
                              { ...link, favorite: !link.favorite },
                              "links",
                            );
                            await load();
                          } catch (e) {
                            notify((e as Error).message);
                          }
                        }}
                      >
                        {link.favorite ? "★" : "☆"}
                      </button>
                      <button onClick={() => edit(link, "links")}>
                        Editar {link.title}
                      </button>
                      <button onClick={() => remove(link, "links")}>
                        Excluir {link.title}
                      </button>
                    </div>
                  </article>
                ))}
              </div>
              {!selected.length && <p>Nenhum link nesta seleção.</p>}
            </details>
          );
        })}
      </div>
      {!drawers.length && <p>Crie sua primeira gaveta.</p>}
      <p>
        Páginas externas geralmente precisam de internet. O cofre offline ainda
        não inclui gavetas ou links.
      </p>
    </>
  );
}
