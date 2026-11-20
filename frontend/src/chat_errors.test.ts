import { describe, it, expect } from "vitest";
import { chatFailure, chatHttpFailure } from "./chat_errors";
describe("chat transport errors", () => {
  it("explains a broken browser stream without claiming the reply was saved or lost", () => {
    for (const message of [
      "NetworkError when attempting to fetch resource.",
      "Failed to fetch",
      "Load failed",
    ]) {
      const translated = chatFailure(new TypeError(message));
      expect(translated).toContain("Reabra a conversa");
      expect(translated).not.toContain(message);
    }
  });
  it("does not expose raw proxy HTML parse errors", () => {
    expect(chatFailure(new SyntaxError("Unexpected token '<'"))).toContain(
      "resposta inválida ou incompleta",
    );
  });
  it("keeps a confirmed backend resource error", () => {
    expect(chatFailure(new Error("Memória insuficiente"))).toBe(
      "Memória insuficiente",
    );
  });
  it("handles proxy HTML and preserves backend JSON explanations", async () => {
    expect(
      await chatHttpFailure(
        new Response("<html>gateway timeout</html>", { status: 504 }),
      ),
    ).toContain("HTTP 504");
    expect(
      await chatHttpFailure(
        new Response(JSON.stringify({ detail: "Modelo local indisponível" }), {
          status: 503,
        }),
      ),
    ).toBe("Modelo local indisponível");
  });
});
