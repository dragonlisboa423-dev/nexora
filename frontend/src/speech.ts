export type VoiceInfo = {
  id: string;
  uri: string;
  name: string;
  language: string;
  provider: string;
  model: string;
  license: string;
  quality: string;
  available: boolean;
  installed: boolean;
  offline_device: boolean;
  offline_server: boolean;
  capabilities: {
    pcm: boolean;
    rate: boolean;
    pitch: boolean;
    word_timestamps: boolean;
  };
};
export interface VoiceCatalogProvider {
  catalog(
    signal?: AbortSignal,
  ): Promise<{
    providers: {
      id: string;
      name: string;
      available: boolean;
      status: string;
      detail: string;
      license: string;
      voices: VoiceInfo[];
    }[];
    candidates: { id: string; status: string; detail: string }[];
  }>;
}
export interface SpeechProvider {
  synthesize(
    text: string,
    rate: number,
    pitch: number,
    signal: AbortSignal,
  ): Promise<ArrayBuffer>;
}
export const serverSpeech: SpeechProvider & VoiceCatalogProvider = {
  async catalog(signal) {
    const response = await fetch("/api/voices", { signal });
    if (!response.ok)
      throw new Error(
        "Catálogo de voz do servidor indisponível ou sessão expirada.",
      );
    return response.json();
  },
  async synthesize(text, rate, pitch, signal) {
    const response = await fetch("/api/voices/synthesize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice_id: "pt-br-f3", rate, pitch }),
      signal,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(
        typeof body.detail === "string"
          ? body.detail
          : "Síntese local indisponível.",
      );
    }
    if (!response.headers.get("content-type")?.startsWith("audio/wav"))
      throw new Error("O servidor não retornou um arquivo de áudio válido.");
    return response.arrayBuffer();
  },
};
