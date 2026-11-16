import { useState } from "react";
import {
  cents,
  money,
  emptyPurchase,
  emptyDrawer,
  emptyLink,
  purchaseFields,
  drawerFields,
  linkFields,
} from "../Personal";
import { queueEdit } from "./sync";
import type { PersonalKind, RecordData, VaultState } from "./vault";

const extras: PersonalKind[] = ["purchases", "drawers", "links"];
const base = ["memories", "reminders", "documents"] as const;
const labels: Record<string, string> = {
  product: "Produto",
  price_cents: "Preço unitário",
  quantity: "Quantidade",
  store_name: "Loja",
  purchased_on: "Data da compra",
  category: "Categoria",
  shipping_cents: "Frete",
  discount_cents: "Desconto",
  payment_method: "Forma de pagamento",
  installments: "Parcelas",
  status: "Estado manual",
  expected_on: "Entrega prevista",
  received_on: "Recebida em",
  warranty_until: "Garantia até",
  return_until: "Devolução até",
  notes: "Observações",
  name: "Nome da gaveta",
  color: "Cor",
  icon: "Ícone",
  position: "Posição",
  title: "Título do link",
  url: "URL",
  description: "Descrição",
  drawer_id: "Gaveta",
  tags: "Etiquetas",
  favorite: "Favorito",
  allow_http: "Permitir HTTP explicitamente",
};
const options: Record<string, Record<string, string>> = {
  status: {
    purchased: "Realizada",
    awaiting: "Aguardando entrega",
    delivered: "Entregue",
    wishlist: "Desejo",
    planned: "Planejada",
    cancelled: "Cancelada",
  },
  icon: {
    folder: "Gaveta",
    book: "Livro",
    star: "Estrela",
    science: "Ciência",
    home: "Casa",
  },
};
export default function PersonalOffline({
  state,
  save,
  busy,
  online,
  fail,
  enable,
}: {
  state: VaultState;
  save: (next: VaultState) => Promise<void>;
  busy: boolean;
  online: boolean;
  fail: (s: string) => void;
  enable: () => Promise<void>;
}) {
  const enabled = extras.every((k) => state.enabledKinds?.includes(k));
  const [kind, setKind] = useState<PersonalKind>("purchases"),
    [draft, setDraft] = useState<RecordData | null>(null),
    [query, setQuery] = useState("");
  const rows = state.entities[kind] ?? [],
    keys =
      kind === "purchases"
        ? purchaseFields
        : kind === "drawers"
          ? drawerFields
          : linkFields;
  function change(field: string, value: unknown) {
    setDraft((d) => (d ? { ...d, [field]: value } : d));
  }
  return (
    <section className="card">
      <h2>Compras e Espaço locais</h2>
      <p>
        Cópia criptografada opcional de registros financeiros, gavetas e links.
        Comprovantes e novos alarmes não são copiados. Orçamentos são uma
        fotografia para consulta. Páginas externas precisam de rede.
      </p>
      {!enabled ? (
        <button
          disabled={busy || !online}
          onClick={async () => {
            if (
              !confirm(
                "Autorizar copiar compras, orçamento, gavetas e links para este cofre criptografado?",
              )
            )
              return;
            try {
              await enable();
            } catch (e) {
              fail((e as Error).message);
            }
          }}
        >
          Autorizar cópia de Compras e Espaço
        </button>
      ) : (
        <>
          <div className="toolbar">
            <label>
              Área local
              <select
                aria-label="Área local"
                value={kind}
                onChange={(e) => {
                  setKind(e.target.value as PersonalKind);
                  setDraft(null);
                }}
              >
                <option value="purchases">Compras</option>
                <option value="drawers">Gavetas</option>
                <option value="links">Links</option>
              </select>
            </label>
            <label>
              Pesquisar registros locais
              <input value={query} onChange={(e) => setQuery(e.target.value)} />
            </label>
            <button
              disabled={busy}
              onClick={() => {
                const value =
                  kind === "purchases"
                    ? emptyPurchase()
                    : kind === "drawers"
                      ? emptyDrawer()
                      : emptyLink(state.entities.drawers?.[0]?.id ?? "");
                setDraft({
                  ...value,
                  id: crypto.randomUUID().replaceAll("-", ""),
                  revision: 0,
                });
              }}
            >
              + Registro pessoal local
            </button>
          </div>
          {draft && (
            <form
              aria-label="Editor pessoal local"
              onSubmit={async (e) => {
                e.preventDefault();
                if (
                  !confirm(
                    "Guardar este rascunho e autorizar sincronização com validação de versão?",
                  )
                )
                  return;
                try {
                  const payload = Object.fromEntries(
                    keys.map((k) => [k, draft[k]]),
                  );
                  if (kind === "purchases") {
                    const total =
                      Number(draft.price_cents) * Number(draft.quantity) +
                      Number(draft.shipping_cents) -
                      Number(draft.discount_cents);
                    if (total < 0 || !Number.isSafeInteger(total))
                      throw new Error("Total inválido.");
                  }
                  await save(
                    queueEdit(state, kind, draft.id, payload, "upsert", true),
                  );
                  setDraft(null);
                } catch (e) {
                  fail((e as Error).message);
                }
              }}
            >
              <h3>Rascunho local · {kind}</h3>
              <p>
                O servidor valida o esquema completo ao sincronizar. Erros
                mantêm o rascunho como conflito para revisão.
              </p>
              <div className="form-grid">
                {keys.map((field) => {
                  const value = draft[field];
                  if (field.endsWith("_cents"))
                    return (
                      <label key={field}>
                        {labels[field]} em reais
                        <input
                          key={draft.id + "-" + field}
                          required
                          inputMode="decimal"
                          defaultValue={(Number(value ?? 0) / 100).toFixed(2)}
                          onChange={(e) => {
                            try {
                              change(field, cents(e.target.value));
                              e.target.setCustomValidity("");
                            } catch (error) {
                              e.target.setCustomValidity(
                                (error as Error).message,
                              );
                            }
                          }}
                        />
                      </label>
                    );
                  if (["favorite", "allow_http"].includes(field))
                    return (
                      <label key={field}>
                        <input
                          type="checkbox"
                          checked={Boolean(value)}
                          onChange={(e) => change(field, e.target.checked)}
                        />
                        {labels[field]}
                      </label>
                    );
                  if (options[field])
                    return (
                      <label key={field}>
                        {labels[field]}
                        <select
                          value={String(value)}
                          onChange={(e) => change(field, e.target.value)}
                        >
                          {Object.entries(options[field]).map(([v, l]) => (
                            <option value={v} key={v}>
                              {l}
                            </option>
                          ))}
                        </select>
                      </label>
                    );
                  if (field === "drawer_id")
                    return (
                      <label key={field}>
                        Gaveta
                        <select
                          required
                          value={String(value)}
                          onChange={(e) => change(field, e.target.value)}
                        >
                          <option value="">Escolha uma gaveta</option>
                          {state.entities.drawers?.map((d) => (
                            <option value={d.id} key={d.id}>
                              {String(d.name)}
                            </option>
                          ))}
                        </select>
                      </label>
                    );
                  return (
                    <label key={field}>
                      {labels[field]}
                      <input
                        required={[
                          "product",
                          "title",
                          "url",
                          "name",
                          "category",
                        ].includes(field)}
                        type={
                          ["quantity", "installments", "position"].includes(
                            field,
                          )
                            ? "number"
                            : field.endsWith("_on") || field.endsWith("_until")
                              ? "date"
                              : field === "color"
                                ? "color"
                                : "text"
                        }
                        min={field === "position" ? 0 : 1}
                        value={
                          field === "tags"
                            ? (value as string[]).join(",")
                            : String(value ?? "")
                        }
                        onChange={(e) =>
                          change(
                            field,
                            field === "tags"
                              ? e.target.value
                                  .split(",")
                                  .map((s) => s.trim())
                                  .filter(Boolean)
                              : [
                                    "quantity",
                                    "installments",
                                    "position",
                                  ].includes(field)
                                ? e.target.value
                                  ? Number(e.target.value)
                                  : null
                                : e.target.value || null,
                          )
                        }
                      />
                    </label>
                  );
                })}
              </div>
              <button disabled={busy}>Guardar rascunho pessoal</button>
              <button type="button" onClick={() => setDraft(null)}>
                Cancelar edição
              </button>
            </form>
          )}
          {rows
            .filter((r) =>
              JSON.stringify(r).toLowerCase().includes(query.toLowerCase()),
            )
            .map((record) => (
              <article key={record.id} className="link-card">
                <h3>{String(record.product ?? record.title ?? record.name)}</h3>
                {kind === "purchases" && (
                  <p>
                    Total calculado:{" "}
                    {money(
                      Number(record.price_cents) * Number(record.quantity) +
                        Number(record.shipping_cents) -
                        Number(record.discount_cents),
                    )}
                  </p>
                )}
                {kind === "links" && (
                  <p className="url-text">
                    {String(record.url)} · abrir links externos exige rede;
                    revise a URL no espaço online.
                  </p>
                )}
                <details>
                  <summary>Dados locais</summary>
                  <pre className="tool-result">
                    {JSON.stringify(record, null, 2)}
                  </pre>
                </details>
                <button disabled={busy} onClick={() => setDraft(record)}>
                  Editar registro local
                </button>
                <button
                  disabled={busy}
                  onClick={async () => {
                    if (
                      !confirm(
                        "Excluir este registro após sincronizar? Gavetas excluem seus links; compras excluem comprovantes e cancelam alarmes no servidor.",
                      )
                    )
                      return;
                    try {
                      await save(
                        queueEdit(state, kind, record.id, {}, "delete", true),
                      );
                    } catch (e) {
                      fail((e as Error).message);
                    }
                  }}
                >
                  Excluir registro local
                </button>
              </article>
            ))}
          <details>
            <summary>Orçamentos copiados para consulta</summary>
            <pre className="tool-result">
              {JSON.stringify(state.personalBudgets ?? {}, null, 2)}
            </pre>
          </details>
          <button
            disabled={busy}
            onClick={async () => {
              if (
                state.pending.some((op) =>
                  extras.includes(op.entity_type as PersonalKind),
                )
              ) {
                fail(
                  "Sincronize ou resolva a fila pessoal antes de remover a cópia.",
                );
                return;
              }
              if (
                !confirm(
                  "Remover somente a cópia pessoal deste cofre? Os registros do servidor serão preservados.",
                )
              )
                return;
              const next = structuredClone(state);
              next.enabledKinds = [...base];
              delete next.personalBudgets;
              for (const k of extras) delete next.entities[k];
              await save(next);
            }}
          >
            Remover cópia local de Compras e Espaço
          </button>
        </>
      )}
    </section>
  );
}
