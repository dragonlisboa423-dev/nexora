export async function api(path: string, options: RequestInit = {}) {
  const res = await fetch("/api" + path, {
    ...options,
    headers: {
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      "X-Saly-Request": "1",
      ...options.headers,
    },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Falha na requisição (${res.status})`,
    );
  }
  return res.json();
}
export const post = (path: string, body: unknown = {}) =>
  api(path, { method: "POST", body: JSON.stringify(body) });
export const put = (path: string, body: unknown) =>
  api(path, { method: "PUT", body: JSON.stringify(body) });
export function download(name: string, data: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export type SalyState =
  | "idle"
  | "listening"
  | "thinking"
  | "responding"
  | "speaking"
  | "paused"
  | "executing"
  | "error"
  | "transcribing"
  | "searching"
  | "reading_document"
  | "executing_tool"
  | "success"
  | "offline";
export type Prefs = {
  collectionName?: string;
  notifications?: {
    enabled: boolean;
    quietStart: string;
    quietEnd: string;
    timezone: string;
    minimumImportance: number;
  };
  voice: {
    voiceURI: string;
    rate: number;
    pitch: number;
    volume: number;
    autoSpeak: boolean;
    profiles: {
      name: string;
      voiceURI: string;
      rate: number;
      pitch: number;
      volume: number;
    }[];
  };
  personality: Record<string, string>;
  privacy: Record<string, boolean>;
  graphics: "auto" | "low" | "high" | "2d";
};
