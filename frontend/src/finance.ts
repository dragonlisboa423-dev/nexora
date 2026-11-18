export const money = (cents: number) =>
  (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
export function cents(value: string): number {
  if (!/^\d{1,10}([.,]\d{1,2})?$/.test(value))
    throw new Error(
      "Use valor positivo com até duas casas decimais, sem separador de milhar.",
    );
  const [whole, fraction = ""] = value.replace(",", ".").split(".");
  const result = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  if (!Number.isSafeInteger(result)) throw new Error("Valor acima do limite.");
  return result;
}
export function spendingSeries(items: Record<string, any>[], month: string) {
  const [year, number] = month.split("-").map(Number);
  return Array.from({ length: 6 }, (_, i) => {
    const date = new Date(year, number - 1 - (5 - i), 15),
      key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
    return {
      month: key,
      label: date.toLocaleDateString("pt-BR", { month: "short" }),
      cents: items
        .filter(
          (item) =>
            ["purchased", "awaiting", "delivered"].includes(item.status) &&
            item.purchased_on?.startsWith(key),
        )
        .reduce((sum, item) => sum + item.total_cents, 0),
    };
  });
}
