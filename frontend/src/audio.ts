import { useEffect, useRef, useState } from "react";
import type { Prefs, SalyState } from "./api";
import { serverSpeech } from "./speech";
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
  onspeechstart: () => void;
  onspeechend: () => void;
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
  const speechSignal = useRef(false),
    speechContext = useRef<AudioContext | null>(null),
    speechSource = useRef<AudioBufferSourceNode | null>(null),
    speechFrame = useRef(0),
    speechAbort = useRef<AbortController | null>(null),
    speechTick = useRef<(() => void) | null>(null);
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
  async function startMic(wakeMode = false) {
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
      pulse();
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
          if (wakeMode) {
            const match = /\b(saly|sali)\b/i.exec(text);
            if (!match) return;
            text = text
              .slice(match.index + match[0].length)
              .replace(/^[.,:!\s]+/, "");
            pulse();
          }
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
        rec.onspeechstart = () => {
          if (token === generation.current) setState("listening");
        };
        rec.onspeechend = () => {
          if (token === generation.current) setState("transcribing");
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
    speechAbort.current?.abort();
    speechAbort.current = null;
    cancelAnimationFrame(speechFrame.current);
    speechTick.current = null;
    speechSource.current?.stop();
    speechSource.current = null;
    void speechContext.current?.close();
    speechContext.current = null;
    speechSignal.current = false;
    level.current = 0;
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    setState("idle");
  }
  function speak(text: string, prefs: Prefs["voice"]) {
    if (prefs.voiceURI === "saly-espeak:pt-br-f3") {
      void speakPCM(text, prefs);
      return;
    }
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
    u.onboundary = () => {
      if (version === utteranceVersion.current) pulse();
    };
    speechSynthesis.speak(u);
  }
  async function speakPCM(text: string, prefs: Prefs["voice"]) {
    stopMic();
    stopSpeech();
    const version = utteranceVersion.current,
      controller = new AbortController();
    speechAbort.current = controller;
    setState("synthesizing");
    try {
      const audio = new AudioContext();
      speechContext.current = audio;
      await audio.resume();
      const raw = await serverSpeech.synthesize(
        text,
        prefs.rate,
        prefs.pitch,
        controller.signal,
      );
      if (version !== utteranceVersion.current) return;
      const buffer = await audio.decodeAudioData(raw);
      if (version !== utteranceVersion.current) return;
      const source = audio.createBufferSource(),
        gain = audio.createGain(),
        analyser = audio.createAnalyser();
      source.buffer = buffer;
      gain.gain.value = prefs.volume;
      analyser.fftSize = 512;
      source.connect(gain);
      gain.connect(analyser);
      analyser.connect(audio.destination);
      const samples = new Uint8Array(analyser.fftSize);
      const tick = () => {
        if (version !== utteranceVersion.current || audio.state !== "running")
          return;
        analyser.getByteTimeDomainData(samples);
        level.current = Math.min(
          1,
          Math.sqrt(
            samples.reduce(
              (sum, value) => sum + ((value - 128) / 128) ** 2,
              0,
            ) / samples.length,
          ) * 5,
        );
        speechFrame.current = requestAnimationFrame(tick);
      };
      speechSource.current = source;
      speechTick.current = tick;
      speechSignal.current = true;
      source.onended = () => {
        if (version !== utteranceVersion.current) return;
        cancelAnimationFrame(speechFrame.current);
        level.current = 0;
        speechSignal.current = false;
        speechSource.current = null;
        speechContext.current = null;
        void audio.close();
        setState("idle");
      };
      source.start();
      tick();
      setState("speaking");
      pulse();
    } catch (error) {
      if (
        version !== utteranceVersion.current ||
        (error as Error).name === "AbortError"
      )
        return;
      cancelAnimationFrame(speechFrame.current);
      speechSignal.current = false;
      level.current = 0;
      void speechContext.current?.close();
      speechContext.current = null;
      setState("error");
      setError(
        (error as Error).message ||
          "Reprodução bloqueada. Clique em Ouvir e confira a permissão de áudio.",
      );
    }
  }
  async function pause() {
    if (speechSignal.current && speechContext.current) {
      const audio = speechContext.current,
        version = utteranceVersion.current;
      try {
        await audio.suspend();
        if (version !== utteranceVersion.current) return;
        cancelAnimationFrame(speechFrame.current);
        level.current = 0;
        setState("paused");
      } catch {
        if (version === utteranceVersion.current)
          setError("A reprodução terminou antes da pausa.");
      }
    } else if ("speechSynthesis" in window) speechSynthesis.pause();
  }
  async function resume() {
    if (speechSignal.current && speechContext.current) {
      const audio = speechContext.current,
        version = utteranceVersion.current;
      try {
        await audio.resume();
        if (version !== utteranceVersion.current) return;
        speechTick.current?.();
        setState("speaking");
      } catch {
        if (version === utteranceVersion.current)
          setError("Não foi possível retomar este áudio.");
      }
    } else if ("speechSynthesis" in window) speechSynthesis.resume();
  }
  useEffect(
    () => () => {
      generation.current++;
      recognition.current?.abort();
      stream.current?.getTracks().forEach((t) => t.stop());
      cancelAnimationFrame(frame.current);
      void ctx.current?.close();
      utteranceVersion.current++;
      speechAbort.current?.abort();
      cancelAnimationFrame(speechFrame.current);
      speechSource.current?.stop();
      void speechContext.current?.close();
      level.current = 0;
      if ("speechSynthesis" in window) speechSynthesis.cancel();
    },
    [],
  );
  return {
    level,
    speechSignal,
    listening,
    voices,
    startMic,
    stopMic,
    speak,
    stopSpeech,
    pause,
    resume,
  };
}
