/** Opt-in encrypted IndexedDB. The unlock key and provider secrets are never persisted. */
export type BaseKind = "memories" | "reminders" | "documents";
export type PersonalKind = "purchases" | "drawers" | "links";
export type Kind = BaseKind | PersonalKind;
export type WritableKind = Exclude<Kind, "documents">;
export type RecordData = {
  id: string;
  revision: number;
  [key: string]: unknown;
};
export type Operation = {
  id: string;
  entity_type: WritableKind;
  entity_id: string;
  action: "upsert" | "delete";
  base_revision: number;
  payload: Record<string, unknown>;
  confirmed: boolean;
  attempted?: boolean;
};
export type SyncResult = {
  id: string;
  status: "applied" | "conflict" | "invalid";
  revision?: number;
  record?: RecordData | null;
  deleted?: boolean;
  detail?: string;
};
export type VaultState = {
  format: 1;
  storageRevision: number;
  vaultSalt?: string;
  cursor: number;
  entities: Record<BaseKind, RecordData[]> &
    Partial<Record<PersonalKind, RecordData[]>>;
  enabledKinds?: Kind[];
  personalBudgets?: Record<string, number>;
  preferences: Record<string, unknown>;
  pending: Operation[];
  conflicts: Record<string, SyncResult>;
  documents: Record<
    string,
    { record: RecordData; originalBase64: string; mime: string }
  >;
  paused: boolean;
  lastSync?: string;
};
type Envelope = {
  id: "encrypted";
  format: 1;
  iterations: 210000;
  revision: number;
  salt: string;
  iv: string;
  ciphertext: string;
  restored?: boolean;
};
const DATABASE = "saly-private-vault";
const MAX_BYTES = 30 * 1024 * 1024;

export function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 16384)
    binary += String.fromCharCode(...bytes.subarray(i, i + 16384));
  return btoa(binary);
}
export function base64ToBytes(value: string): Uint8Array {
  return Uint8Array.from(atob(value), (char) => char.charCodeAt(0));
}
function secureContext() {
  if (!globalThis.crypto?.subtle || !globalThis.indexedDB)
    throw new Error("O cofre exige HTTPS e suporte a Web Crypto/IndexedDB.");
}
function open(): Promise<IDBDatabase> {
  secureContext();
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE, 1);
    request.onupgradeneeded = () =>
      request.result.createObjectStore("vault", { keyPath: "id" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () =>
      reject(new Error("Não foi possível abrir o armazenamento local."));
    request.onblocked = () =>
      reject(new Error("Feche outras abas da SALY para atualizar o cofre."));
  });
}
async function envelope(): Promise<Envelope | null> {
  const db = await open();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction("vault", "readonly");
    const request = transaction.objectStore("vault").get("encrypted");
    request.onsuccess = () => resolve(request.result ?? null);
    request.onerror = () => reject(new Error("Falha ao ler o cofre local."));
    transaction.oncomplete = () => db.close();
    transaction.onabort = () => db.close();
  });
}
export const vaultExists = async () => Boolean(await envelope());
function validateEnvelope(value: unknown): asserts value is Envelope {
  const item = value as Partial<Envelope> | null;
  if (
    !item ||
    item.id !== "encrypted" ||
    item.format !== 1 ||
    item.iterations !== 210000 ||
    !Number.isSafeInteger(item.revision) ||
    item.revision! < 1 ||
    typeof item.salt !== "string" ||
    typeof item.iv !== "string" ||
    typeof item.ciphertext !== "string" ||
    item.ciphertext.length > MAX_BYTES * 2 ||
    base64ToBytes(item.salt).length !== 16 ||
    base64ToBytes(item.iv).length !== 12
  )
    throw new Error("Backup criptografado inválido ou incompatível.");
}
function validateState(state: VaultState) {
  if (
    state.format !== 1 ||
    !Number.isSafeInteger(state.cursor) ||
    !Array.isArray(state.pending) ||
    !state.entities ||
    !state.documents ||
    !state.conflicts
  )
    throw new Error("Schema do cofre incompatível.");
  const supported = [
    "memories",
    "reminders",
    "documents",
    "purchases",
    "drawers",
    "links",
  ];
  if (state.enabledKinds?.some((kind) => !supported.includes(kind)))
    throw new Error("Tipos locais incompatíveis.");
  for (const kind of state.enabledKinds ??
    (["memories", "reminders", "documents"] as Kind[])) {
    if (
      !Array.isArray(state.entities[kind]) ||
      state.entities[kind].some(
        (record) =>
          typeof record.id !== "string" ||
          !Number.isSafeInteger(record.revision),
      )
    )
      throw new Error("Registros locais inválidos.");
  }
}
function aad(
  item: Pick<Envelope, "format" | "iterations" | "revision" | "salt">,
) {
  return new TextEncoder().encode(
    JSON.stringify([item.format, item.iterations, item.revision, item.salt]),
  );
}
async function derive(passphrase: string, salt: Uint8Array) {
  if (passphrase.length < 8 || passphrase.length > 200)
    throw new Error(
      "Use uma senha do cofre entre 8 e 200 caracteres, diferente da senha de acesso e das chaves de API.",
    );
  const material = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(passphrase),
    "PBKDF2",
    false,
    ["deriveKey"],
  );
  return crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      hash: "SHA-256",
      iterations: 210000,
      salt: salt as BufferSource,
    },
    material,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}
async function writeEnvelope(
  item: Envelope,
  expectedRevision: number | null,
  expectedSalt?: string,
) {
  const db = await open();
  return new Promise<void>((resolve, reject) => {
    const transaction = db.transaction("vault", "readwrite");
    let conflict = false;
    const store = transaction.objectStore("vault");
    const current = store.get("encrypted");
    current.onsuccess = () => {
      if (
        expectedRevision !== null &&
        ((current.result?.revision ?? 0) !== expectedRevision ||
          current.result?.salt !== expectedSalt)
      ) {
        conflict = true;
        transaction.abort();
        return;
      }
      store.put(item);
    };
    transaction.oncomplete = () => {
      db.close();
      resolve();
    };
    transaction.onabort = () => {
      db.close();
      reject(
        new Error(
          conflict
            ? "O cofre mudou em outra aba. Bloqueie e abra novamente antes de editar."
            : "Falha no armazenamento local; espaço insuficiente ou gravação interrompida. Exporte um backup.",
        ),
      );
    };
    transaction.onerror = () => {}; // onabort reports a sanitized error.
  });
}
export async function saveVault(
  key: CryptoKey,
  state: VaultState,
  salt?: string,
): Promise<VaultState> {
  validateState(state);
  const old = await envelope();
  if (old && !salt && old.salt !== state.vaultSalt)
    throw new Error(
      "Este cofre foi substituído em outra aba. Bloqueie e abra novamente.",
    );
  const next = {
    ...state,
    storageRevision: state.storageRevision + 1,
    vaultSalt: salt ?? state.vaultSalt,
  };
  const plaintext = new TextEncoder().encode(JSON.stringify(next));
  if (plaintext.byteLength > MAX_BYTES)
    throw new Error(
      "Cofre acima do limite de 30 MB. Remova documentos locais ou exporte antes de continuar.",
    );
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const item: Envelope = {
    id: "encrypted",
    format: 1,
    iterations: 210000,
    revision: next.storageRevision,
    salt: salt ?? old?.salt ?? "",
    iv: bytesToBase64(iv),
    ciphertext: "",
    restored: next.paused,
  };
  item.ciphertext = bytesToBase64(
    new Uint8Array(
      await crypto.subtle.encrypt(
        {
          name: "AES-GCM",
          iv: iv as BufferSource,
          additionalData: aad(item) as BufferSource,
        },
        key,
        plaintext,
      ),
    ),
  );
  await writeEnvelope(item, state.storageRevision, old?.salt);
  return next;
}
export async function createVault(passphrase: string, state: VaultState) {
  if (await vaultExists())
    throw new Error(
      "Já existe um cofre neste navegador. Desbloqueie ou faça backup antes de substituí-lo.",
    );
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const key = await derive(passphrase, salt);
  return { key, state: await saveVault(key, state, bytesToBase64(salt)) };
}
async function decryptEnvelope(item: Envelope, passphrase: string) {
  const key = await derive(passphrase, base64ToBytes(item.salt));
  try {
    const bytes = await crypto.subtle.decrypt(
      {
        name: "AES-GCM",
        iv: base64ToBytes(item.iv) as BufferSource,
        additionalData: aad(item) as BufferSource,
      },
      key,
      base64ToBytes(item.ciphertext) as BufferSource,
    );
    const state: VaultState = JSON.parse(new TextDecoder().decode(bytes));
    validateState(state);
    if (
      state.storageRevision !== item.revision ||
      state.vaultSalt !== item.salt
    )
      throw new Error("Revision mismatch");
    return {
      key,
      state: { ...state, paused: Boolean(state.paused || item.restored) },
    };
  } catch {
    throw new Error(
      "Senha do cofre incorreta ou backup danificado. Nenhum dado foi desbloqueado.",
    );
  }
}
export async function unlockVault(passphrase: string) {
  const item = await envelope();
  validateEnvelope(item);
  return decryptEnvelope(item, passphrase);
}
export async function encryptedBackup() {
  const item = await envelope();
  validateEnvelope(item);
  return item;
}
export async function restoreBackup(value: unknown, passphrase: string) {
  validateEnvelope(value);
  const opened = await decryptEnvelope(value, passphrase);
  const current = await envelope();
  await saveVault(
    opened.key,
    { ...opened.state, storageRevision: current?.revision ?? 0, paused: true },
    value.salt,
  );
}
export async function clearVault() {
  return new Promise<void>((resolve, reject) => {
    const request = indexedDB.deleteDatabase(DATABASE);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(new Error("Falha ao limpar dados locais."));
    request.onblocked = () =>
      reject(
        new Error("Feche as outras abas da SALY antes de remover o cofre."),
      );
  });
}
