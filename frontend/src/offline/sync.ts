import { api } from "../api";
import type {
  Kind,
  Operation,
  RecordData,
  SyncResult,
  VaultState,
} from "./vault";

export async function initialState(signal?: AbortSignal): Promise<VaultState> {
  const [snapshot, preferences] = await Promise.all([
    api("/sync/bootstrap", { signal }),
    api("/settings", { signal }),
  ]);
  return {
    format: 1,
    storageRevision: 0,
    cursor: snapshot.cursor,
    entities: snapshot.entities,
    preferences,
    pending: [],
    conflicts: {},
    documents: {},
    paused: false,
  };
}
function replaceRecord(
  state: VaultState,
  kind: Kind,
  id: string,
  record: RecordData | null,
) {
  state.entities[kind] = state.entities[kind].filter((item) => item.id !== id);
  if (record) state.entities[kind].push(record);
  if (kind === "documents" && !record) delete state.documents[id];
}
export function queueEdit(
  state: VaultState,
  kind: "memories" | "reminders",
  id: string,
  payload: Record<string, unknown>,
  action: "upsert" | "delete",
  confirmed: boolean,
): VaultState {
  const next = structuredClone(state);
  const previous = next.pending.find(
    (item) => item.entity_type === kind && item.entity_id === id,
  );
  if (previous?.attempted)
    throw new Error(
      "Esta alteração já foi enviada ou está em conflito. Sincronize ou revise o conflito antes de editar novamente.",
    );
  const current = next.entities[kind].find((record) => record.id === id);
  const operation: Operation = {
    id: previous?.id ?? crypto.randomUUID(),
    entity_type: kind,
    entity_id: id,
    action,
    payload,
    confirmed,
    base_revision: previous?.base_revision ?? current?.revision ?? 0,
  };
  next.pending = next.pending.filter((item) => item !== previous);
  if (action === "delete" && operation.base_revision === 0) {
    replaceRecord(next, kind, id, null);
    return next;
  }
  next.pending.push(operation);
  replaceRecord(
    next,
    kind,
    id,
    action === "delete"
      ? null
      : { ...payload, id, revision: operation.base_revision },
  );
  return next;
}
export function resolveConflict(
  state: VaultState,
  operationId: string,
  useLocal: boolean,
): VaultState {
  const next = structuredClone(state);
  const operation = next.pending.find((item) => item.id === operationId),
    conflict = next.conflicts[operationId];
  if (!operation || !conflict) throw new Error("Conflito não encontrado.");
  next.pending = next.pending.filter((item) => item.id !== operationId);
  delete next.conflicts[operationId];
  replaceRecord(
    next,
    operation.entity_type,
    operation.entity_id,
    conflict.record ?? null,
  );
  if (useLocal) {
    if (conflict.deleted && operation.action === "delete") return next;
    const newId = conflict.deleted
      ? crypto.randomUUID().replaceAll("-", "")
      : operation.entity_id;
    next.pending.push({
      ...operation,
      id: crypto.randomUUID(),
      entity_id: newId,
      base_revision: conflict.deleted ? 0 : (conflict.revision ?? 0),
      attempted: false,
    });
    if (operation.action === "upsert")
      replaceRecord(next, operation.entity_type, newId, {
        ...operation.payload,
        id: newId,
        revision: conflict.deleted ? 0 : (conflict.revision ?? 0),
      });
  }
  return next;
}
export async function synchronize(
  state: VaultState,
  persist: (value: VaultState) => Promise<VaultState>,
  signal?: AbortSignal,
) {
  let next = structuredClone(state);
  if (next.paused)
    throw new Error(
      "Sincronização pausada após restauração. Revise a fila e autorize antes de enviar.",
    );
  const pending = next.pending
    .filter((item) => !next.conflicts[item.id])
    .slice(0, 100);
  if (pending.length) {
    const ids = new Set(pending.map((item) => item.id));
    next.pending.forEach((item) => {
      if (ids.has(item.id)) item.attempted = true;
    });
    next = await persist(next); // Receipt keys/payload survive loss of the response or a reload.
    const response: { results: SyncResult[] } = await api("/sync/push", {
      method: "POST",
      body: JSON.stringify({
        operations: pending.map(({ attempted, ...operation }) => operation),
      }),
      signal,
    });
    for (const result of response.results) {
      const operation = next.pending.find((item) => item.id === result.id);
      if (!operation) continue;
      if (result.status === "applied") {
        next.pending = next.pending.filter((item) => item.id !== result.id);
        replaceRecord(
          next,
          operation.entity_type,
          operation.entity_id,
          result.record ?? null,
        );
      } else next.conflicts[result.id] = result;
    }
    next = await persist(next);
  }
  for (let page = 0; page < 20; page++) {
    const response = await api(`/sync/pull?after=${next.cursor}`, { signal });
    for (const change of response.changes as {
      kind: Kind;
      entity_id: string;
      revision: number;
      deleted: boolean;
      record: RecordData | null;
    }[]) {
      const pendingOperation = next.pending.find(
        (item) =>
          item.entity_type === change.kind &&
          item.entity_id === change.entity_id,
      );
      if (pendingOperation) {
        const revision = change.record?.revision ?? change.revision;
        if (revision !== pendingOperation.base_revision)
          next.conflicts[pendingOperation.id] = {
            id: pendingOperation.id,
            status: "conflict",
            record: change.record,
            revision,
            deleted: change.deleted,
            detail: "Alteração remota ou exclusão: revise as duas versões.",
          };
      } else replaceRecord(next, change.kind, change.entity_id, change.record);
    }
    next.cursor = response.cursor;
    next.lastSync = new Date().toISOString();
    next = await persist(next);
    if (!response.has_more) break;
  }
  return next;
}
