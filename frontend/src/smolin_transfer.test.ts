import { describe, it, expect } from "vitest";
import { smolinError, uploadResponse } from "./smolin_transfer";
describe("respostas reais do upload", () => {
  it("trata HTML também na criação/conclusão do envio em blocos", () => {
    expect(
      smolinError(new SyntaxError("Unexpected token '<' PRIVATE_HTML")),
    ).toContain("servidor/proxy");
    expect(smolinError(new SyntaxError("PRIVATE_HTML"))).not.toContain(
      "PRIVATE_HTML",
    );
  });
  it("explica HTML do proxy sem vazar o HTML nem lançar SyntaxError", () => {
    expect(() =>
      uploadResponse("<html>PRIVATE PROXY PAGE</html>", 413, "text/html"),
    ).toThrow("HTTP 413");
    expect(() =>
      uploadResponse("<html>private</html>", 200, "text/html"),
    ).toThrow("devolveu HTML");
  });
  it("preserva mensagem JSON do servidor e só confirma resposta bem formada", () => {
    expect(() =>
      uploadResponse('{"detail":"Limite de 64 MB"}', 413, "application/json"),
    ).toThrow("64 MB");
    expect(uploadResponse('{"id":"doc","status":"stored_only"}', 200)).toEqual({
      id: "doc",
      status: "stored_only",
    });
  });
});
