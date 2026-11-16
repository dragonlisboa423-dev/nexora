import { useEffect, useState } from "react";
import { serverSpeech } from "./speech";
import type { Prefs, SalyState } from "./api";

type Catalog = Awaited<ReturnType<typeof serverSpeech.catalog>>;
export function ServerVoices({
  prefs,
  save,
  preview,
  stop,
  pause,
  resume,
  speechState,
}: {
  prefs: Prefs;
  save: (prefs: Prefs) => Promise<void>;
  preview: (uri: string, text: string) => void;
  stop: () => void;
  pause: () => void;
  resume: () => void;
  speechState: SalyState;
}) {
  const [catalog, setCatalog] = useState<Catalog | null>(null),
    [error, setError] = useState(""),
    [phrase, setPhrase] = useState(
      "Olá. Sou Saly. Esta é uma amostra de síntese local em português brasileiro.",
    ),
    [provider, setProvider] = useState(""),
    [offlineOnly, setOfflineOnly] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    serverSpeech
      .catalog(controller.signal)
      .then(setCatalog)
      .catch((error) => {
        if (error.name !== "AbortError") setError(error.message);
      });
    return () => controller.abort();
  }, []);
  const voices =
    catalog?.providers
      .flatMap((item) => item.voices)
      .filter(
        (voice) =>
          (!provider || voice.provider === provider) &&
          (!offlineOnly || voice.offline_device),
      ) ?? [];
  return (
    <section className="card" aria-label="Catálogo de vozes independentes">
      <h2>Vozes independentes do navegador</h2>
      <p>
        O motor local do servidor não exige outra API. Para falar pelo celular,
        ainda é necessário alcançar o backend. A variante feminina por formantes
        é artificial; a candidata neural Kokoro permanece não instalada.
      </p>
      {error && <p role="alert">{error}</p>}
      <label>
        Provedor de síntese
        <select
          value={provider}
          onChange={(event) => setProvider(event.target.value)}
        >
          <option value="">Todos os provedores do servidor</option>
          {catalog?.providers.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={offlineOnly}
          onChange={(event) => setOfflineOnly(event.target.checked)}
        />
        Somente vozes que funcionam offline neste dispositivo
      </label>
      <label>
        Frase para prévia
        <textarea
          maxLength={3000}
          value={phrase}
          onChange={(event) => setPhrase(event.target.value)}
        />
      </label>
      {voices.map((voice) => (
        <article className="card" key={voice.id}>
          <h3>{voice.name}</h3>
          <span className="badge">
            {voice.installed
              ? "Motor configurado · teste uma prévia"
              : "Não instalado/configurado"}
          </span>
          <p>
            {voice.language} · {voice.provider} · {voice.model} ·{" "}
            {voice.license}
          </p>
          <p>{voice.quality}</p>
          <p>
            {voice.offline_device
              ? "Offline no dispositivo"
              : "Precisa alcançar o servidor"}{" "}
            · Sem download de modelo no frontend · PCM disponível para animação
            real
          </p>
          <div className="toolbar">
            <button
              disabled={!voice.available || !phrase.trim()}
              onClick={() => preview(voice.uri, phrase)}
            >
              Ouvir prévia local
            </button>
            <button
              className="secondary"
              disabled={!voice.available}
              onClick={() =>
                void save({
                  ...prefs,
                  voice: { ...prefs.voice, voiceURI: voice.uri },
                })
              }
            >
              {prefs.voice.voiceURI === voice.uri
                ? "Voz selecionada"
                : "Selecionar voz local"}
            </button>
            <button
              className="secondary"
              disabled={!voice.available || !phrase.trim()}
              onClick={async () => {
                try {
                  const bytes = await serverSpeech.synthesize(
                    phrase,
                    prefs.voice.rate,
                    prefs.voice.pitch,
                    new AbortController().signal,
                  );
                  const url = URL.createObjectURL(
                    new Blob([bytes], { type: "audio/wav" }),
                  );
                  const link = document.createElement("a");
                  link.href = url;
                  link.download = "saly-voz-local.wav";
                  link.click();
                  setTimeout(() => URL.revokeObjectURL(url), 1000);
                } catch (error) {
                  setError((error as Error).message);
                }
              }}
            >
              Baixar WAV da frase
            </button>
          </div>
        </article>
      ))}
      {!voices.length && <p>Nenhuma voz do servidor atende a este filtro.</p>}
      <p role="status">
        Áudio:{" "}
        {speechState === "speaking"
          ? "reproduzindo"
          : speechState === "paused"
            ? "pausado"
            : speechState === "synthesizing"
              ? "preparando"
              : "sem reprodução ativa"}
      </p>
      <div className="toolbar">
        <button
          className="secondary"
          disabled={speechState !== "speaking"}
          onClick={pause}
        >
          Pausar áudio
        </button>
        <button
          className="secondary"
          disabled={speechState !== "paused"}
          onClick={resume}
        >
          Continuar áudio
        </button>
        <button className="secondary" onClick={stop}>
          Parar áudio
        </button>
      </div>
      {catalog?.candidates.map((item) => (
        <details key={item.id}>
          <summary>{item.id} · não configurado</summary>
          <p>{item.detail}</p>
        </details>
      ))}
    </section>
  );
}
