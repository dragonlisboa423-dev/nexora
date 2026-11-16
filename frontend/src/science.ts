/** Deterministic teaching models; no field measurements or calibrated prediction. */
export function dna(sequence: string) {
  if (!/^[ACGT]{1,60}$/.test(sequence))
    throw new Error("Use 1 a 60 bases A, C, G ou T.");
  const pairs: Record<string, string> = { A: "T", T: "A", C: "G", G: "C" };
  return {
    coding: sequence,
    complement: [...sequence].map((b) => pairs[b]).join(""),
    rna: sequence.replaceAll("T", "U"),
  };
}
export function cross(a: string, b: string) {
  if (!["AA", "Aa", "aa"].includes(a) || !["AA", "Aa", "aa"].includes(b))
    throw new Error("Genótipo inválido");
  return [...a].flatMap((x) => [...b].map((y) => [x, y].sort().join("")));
}
export function ecology(
  initial: number,
  capacity: number,
  rate: number,
  steps = 30,
) {
  if (
    ![initial, capacity, rate, steps].every(Number.isFinite) ||
    initial < 0 ||
    initial > 1000 ||
    capacity < 1 ||
    capacity > 1000 ||
    rate < 0 ||
    rate > 1 ||
    steps < 1 ||
    steps > 100
  )
    throw new Error("Parâmetros fora dos limites");
  const values = [initial];
  for (let t = 1; t <= steps; t++) {
    const previous = values[t - 1],
      factor = Math.exp(rate);
    values.push(
      previous === 0
        ? 0
        : (capacity * previous * factor) / (capacity + previous * (factor - 1)),
    );
  }
  return values;
}
