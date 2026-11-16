import { describe, it, expect } from "vitest";
import { dna, cross, ecology } from "./science";
describe("regras e modelos didáticos", () => {
  it("distingue complemento antiparalelo e RNA da fita codificante", () => {
    expect(dna("ATGC")).toEqual({
      coding: "ATGC",
      complement: "TACG",
      rna: "AUGC",
    });
    expect(() => dna("ACGU")).toThrow();
  });
  it("cruzamento Aa × Aa preserva quatro combinações equiprováveis", () => {
    expect(cross("Aa", "Aa")).toEqual(["AA", "Aa", "Aa", "aa"]);
    expect(cross("AA", "aa")).toEqual(["Aa", "Aa", "Aa", "Aa"]);
  });
  it("logística mantém equilíbrio e aproxima capacidade sem inventar medições", () => {
    expect(ecology(100, 100, 0.2)).toEqual(Array(31).fill(100));
    const values = ecology(20, 100, 0.2);
    expect(values).toHaveLength(31);
    expect(values[30]).toBeGreaterThan(98);
    expect(values.every((v, i) => i === 0 || v >= values[i - 1])).toBe(true);
    expect(ecology(0, 100, 0.2).at(-1)).toBe(0);
    expect(() => ecology(20, 0, 0.2)).toThrow();
  });
});
