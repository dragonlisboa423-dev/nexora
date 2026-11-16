import { describe, expect, it } from "vitest";
import { queueEdit, resolveConflict } from "./sync";
import type { VaultState } from "./vault";

function state(): VaultState {
  return {
    format: 1,
    storageRevision: 1,
    cursor: 5,
    entities: {
      memories: [{ id: "m1", revision: 3, content: "Servidor" }],
      reminders: [],
      documents: [],
    },
    preferences: {},
    pending: [],
    conflicts: {},
    documents: {},
    paused: false,
  };
}
describe("rascunhos offline e conflitos", () => {
  it("coalesce edições ainda não enviadas preservando a revisão de base", () => {
    const first = queueEdit(
      state(),
      "memories",
      "m1",
      { content: "Primeiro" },
      "upsert",
      false,
    );
    const second = queueEdit(
      first,
      "memories",
      "m1",
      { content: "Segundo" },
      "upsert",
      false,
    );
    expect(second.pending).toHaveLength(1);
    expect(second.pending[0].id).toBe(first.pending[0].id);
    expect(second.pending[0].base_revision).toBe(3);
    expect(first.entities.memories[0].content).toBe("Primeiro");
  });
  it("não altera o conteúdo de uma operação cujo resultado pode ter sido perdido", () => {
    const value = queueEdit(
      state(),
      "memories",
      "m1",
      { content: "Enviado" },
      "upsert",
      false,
    );
    value.pending[0].attempted = true;
    expect(() =>
      queueEdit(
        value,
        "memories",
        "m1",
        { content: "Diferente" },
        "upsert",
        false,
      ),
    ).toThrow("já foi enviada");
  });
  it("não recria automaticamente o ID de um registro excluído", () => {
    const value = queueEdit(
      state(),
      "memories",
      "m1",
      { content: "Rascunho" },
      "upsert",
      false,
    );
    const id = value.pending[0].id;
    value.conflicts[id] = {
      id,
      status: "conflict",
      revision: 4,
      record: null,
      deleted: true,
    };
    const server = resolveConflict(value, id, false);
    expect(server.entities.memories).toHaveLength(0);
    expect(server.pending).toHaveLength(0);
    const local = resolveConflict(value, id, true);
    expect(local.pending[0].entity_id).not.toBe("m1");
    expect(local.pending[0].base_revision).toBe(0);
    expect(local.entities.memories[0].content).toBe("Rascunho");
  });
});
