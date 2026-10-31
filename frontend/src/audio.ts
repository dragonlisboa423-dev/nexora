import { useEffect, useRef, useState } from "react";
import type { Prefs, SalyState } from "./api";
// Recognition is vendor-dependent and can transmit audio to a browser provider.
type Recognition = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: (e: any) => void;
  onerror: (e: any) => void;
  onend: () => void;
};
declare global {
  interface Window {
    SpeechRecognition?: new () => Recognition;
    webkitSpeechRecognition?: new () => Recognition;
  }
}
export function useAudio(
  setState: (s: SalyState) => void,
  setError: (s: string) => void,
  onTranscript: (s: string) => void,
  pulse: () => void,
) {
  const level = useRef(0),
    stream = useRef<MediaStream | null>(null),
    ctx = useRef<AudioContext | null>(null),
    frame = useRef(0),
    recognition = useRef<Recognition | null>(null),
    generation = useRef(0),
    utteranceVersion = useRef(0);
  const [listening, setListening] = useState(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  useEffect(() => {
    if (!("speechSynthesis" in window)) return;
    const refresh = () => setVoices(speechSynthesis.getVoices());
    refresh();
    speechSynthesis.addEventListener("voiceschanged", refresh);
    return () => speechSynthesis.removeEventListener("voiceschanged", refresh);
  }, []);
  function stopMic() {
    generation.current++;
    recognition.current?.stop();
    recognition.current = null;
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    cancelAnimationFrame(frame.current);
    void ctx.current?.close();
    ctx.current = null;
    level.current = 0;
    setListening(false);
    setState("idle");
  }
  async function startMic() {
    if (!navigator.mediaDevices?.getUserMedia) {
      setError(
        "Microfone requer navegador compatível e contexto seguro HTTPS ou localhost.",
      );
      return;
    }
    stopSpeech();
    stopMic();
    const token = ++generation.current;
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (token !== generation.current) {
        media.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = media;
      const audio = new AudioContext();
      ctx.current = audio;
      await audio.resume();
      if (token !== generation.current) {
        media.getTracks().forEach((t) => t.stop());
        if (audio.state !== "closed") await audio.close();
        return;
      }
      const analyser = audio.createAnalyser();
      analyser.fftSize = 256;
      audio.createMediaStreamSource(media).connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);
      function tick() {
        analyser.getByteTimeDomainData(samples);
        level.current = Math.min(
          1,
          Math.sqrt(
            samples.reduce((a, v) => a + ((v - 128) / 128) ** 2, 0) /
              samples.length,
          ) * 5,
        );
        frame.current = requestAnimationFrame(tick);
      }
      tick();
      setListening(true);
      setState("listening");
      const Constructor =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      if (Constructor) {
        const rec = new Constructor();
        recognition.current = rec;
        rec.lang = "pt-BR";
        rec.interimResults = true;
        rec.continuous = true;
        rec.onresult = (e) => {
          if (token !== generation.current) return;
          let text = "";
          for (let i = 0; i < e.results.length; i++)
            text += e.results[i][0].transcript + " ";
          onTranscript(text.trim());
        };
        rec.onerror = (e) => {
          if (token !== generation.current) return;
          setError(`Transcrição indisponível: ${e.error}. Você pode digitar.`);
          stopMic();
        };
        rec.onend = () => {
          if (token === generation.current) stopMic();
        };
        rec.start();
      } else {
        setError(
          "Transcrição não suportada neste navegador. O medidor usa áudio real; digite sua mensagem.",
        );
      }
    } catch {
      if (token !== generation.current) return;
      stopMic();
      setError("Não foi possível acessar o microfone. Confira as permissões.");
      setState("error");
    }
  }
  function stopSpeech() {
    utteranceVersion.current++;
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    setState("idle");
  }
  function speak(text: string, prefs: Prefs["voice"]) {
    if (!("speechSynthesis" in window)) {
      setError("Síntese de voz não suportada.");
      return;
    }
    stopMic();
    stopSpeech();
    const version = utteranceVersion.current;
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "pt-BR";
    u.voice =
      voices.find((v) => v.voiceURI === prefs.voiceURI) ||
      voices.find((v) => v.lang === "pt-BR") ||
      null;
    u.rate = prefs.rate;
    u.pitch = prefs.pitch;
    u.volume = prefs.volume;
    u.onstart = () => {
      if (version !== utteranceVersion.current) return;
      setState("speaking");
      pulse();
    };
    u.onpause = () => {
      if (version === utteranceVersion.current) setState("paused");
    };
    u.onresume = () => {
      if (version === utteranceVersion.current) setState("speaking");
    };
    u.onend = () => {
      if (version === utteranceVersion.current) setState("idle");
    };
    u.onerror = (e) => {
      if (version !== utteranceVersion.current) return;
      setState(
        e.error === "canceled" || e.error === "interrupted" ? "idle" : "error",
      );
    };
    speechSynthesis.speak(u);
  }
  useEffect(
    () => () => {
      generation.current++;
      recognition.current?.abort();
      stream.current?.getTracks().forEach((t) => t.stop());
      cancelAnimationFrame(frame.current);
      void ctx.current?.close();
      if ("speechSynthesis" in window) speechSynthesis.cancel();
    },
    [],
  );
  return {
    level,
    listening,
    voices,
    startMic,
    stopMic,
    speak,
    stopSpeech,
    pause: () => speechSynthesis.pause(),
    resume: () => speechSynthesis.resume(),
  };
}
