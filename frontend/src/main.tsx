import { LocalModels } from "./LocalModels";
import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
  Navigate,
} from "react-router-dom";
import {
  MessageCircle,
  CalendarDays,
  History,
  Leaf,
  Activity as ActivityIcon,
  AudioLines,
  Bell,
  Brain,
  ShoppingBag,
  Folder,
  BookOpen,
  Film,
  FlaskConical,
  ChevronLeft,
  ChevronRight,
  Database,
  LogOut,
  Menu,
  Mic,
  Pause,
  Play,
  Plus,
  Send,
  Settings,
  ShieldCheck,
  Square,
  Sparkles,
  Volume2,
  X,
} from "lucide-react";
import { api, post, put, type Prefs, type SalyState } from "./api";
import { lazy, Suspense } from "react";
const Core = lazy(() => import("./Core").then((m) => ({ default: m.Core })));
import { useAudio } from "./audio";
import { voiceCommand } from "./voice_command";
import {
  Activity,
  Evaluation,
  Knowledge,
  Memories,
  SettingsPanel,
  Voices,
} from "./Panels";
import "./style.css";
import "./botanical.css";
import { areaFor, areaLabels, areaLinks } from "./navigation";
const KnowledgeHome = lazy(() =>
  import("./Areas").then((m) => ({ default: m.KnowledgeHome })),
);
const RoutineHome = lazy(() =>
  import("./Areas").then((m) => ({ default: m.RoutineHome })),
);
const AdvancedHome = lazy(() =>
  import("./Areas").then((m) => ({ default: m.AdvancedHome })),
);
const MediaAdvanced = lazy(() =>
  import("./Areas").then((m) => ({ default: m.MediaAdvanced })),
);
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Smolin } from "./Smolin";
import { Approvals, Tools, ReminderAlerts } from "./AgentPanels";
import { emit, transition, useOperations } from "./operations";
import { PwaUpdate } from "./pwa";
const OfflineWorkspace = lazy(() => import("./offline/OfflineWorkspace"));
const PlanningPage = lazy(() =>
  import("./Planning").then((module) => ({ default: module.PlanningPage })),
);
const AlarmsPage = lazy(() =>
  import("./Planning").then((module) => ({ default: module.AlarmsPage })),
);
const Purchases = lazy(() =>
  import("./Personal").then((m) => ({ default: m.Purchases })),
);
const Space = lazy(() =>
  import("./Personal").then((m) => ({ default: m.Space })),
);
const TextBook = lazy(() => import("./TextBook"));
const PdfBook = lazy(() => import("./PdfBook"));
const Studio = lazy(() => import("./Studio"));
const Library = lazy(() => import("./Library"));
import { AlarmNotifier } from "./AlarmNotifier";
import {
  Laboratory,
  VerificationDetails,
  type Verification,
} from "./Laboratory";
import { stateLabels as labels } from "./state_labels";

type Message = {
  role: string;
  content: string;
  partial?: boolean;
  model?: string;
  provider?: string;
  sources?: any[];
  verification?: Verification;
};
function Login({ done }: { done: () => void }) {
  const [setup, setSetup] = useState<boolean | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    api("/bootstrap")
      .then((d) => setSetup(d.needs_setup))
      .catch(() =>
        setError(
          "Não foi possível conectar ao espaço privado. Confira sua conexão.",
        ),
      );
  }, []);
  return (
    <div className="login">
      <div className="login-mark">S</div>
      <small>SALY INTELLIGENCE</small>
      <h1>Uma inteligência. Seu universo.</h1>
      <p>
        Um único espaço. Uma memória contínua.
        <br />
        Acesso exclusivo da proprietária.
      </p>
      {setup === false && (
        <form
          className="card"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            const form = new FormData(e.currentTarget);
            try {
              await post("/auth/login", { password: form.get("password") });
              done();
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <h2>Desbloquear Saly</h2>
          <label>
            Senha privada
            <input
              type="password"
              name="password"
              autoComplete="current-password"
              required
            />
          </label>
          <button disabled={busy}>
            {busy ? "Verificando…" : "Desbloquear"}
          </button>
        </form>
      )}
      {setup === true && (
        <div className="card">
          <h2>Configuração privada pendente</h2>
          <p>
            O acesso deve ser preparado pela proprietária no servidor. Não há
            cadastro público.
          </p>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
      <small>
        Memória única · Documentos privados · Controle da proprietária
      </small>
      {!navigator.onLine && <h2>Saly está sem conexão.</h2>}
      <NavLink to="/offline" className="citation">
        Abrir cofre local sem depender do servidor
      </NavLink>
    </div>
  );
}
function App() {
  const state = useOperations();
  const setState = (value: SalyState) => transition("interaction", value);
  const [historyQuery, setHistoryQuery] = useState("");
  useEffect(() => {
    const lost = () => emit({ type: "CONNECTION_LOST", id: "network" }),
      restored = () => emit({ type: "CONNECTION_RESTORED", id: "network" });
    window.addEventListener("offline", lost);
    window.addEventListener("online", restored);
    if (!navigator.onLine) lost();
    return () => {
      window.removeEventListener("offline", lost);
      window.removeEventListener("online", restored);
    };
  }, []);
  const [auth, setAuth] = useState<boolean | null>(null),
    [prefs, setPrefs] = useState<Prefs | null>(null),
    [health, setHealth] = useState<any>(null),
    [error, setError] = useState(""),
    [input, setInput] = useState(""),
    [messages, setMessages] = useState<Message[]>([]),
    [conversation, setConversation] = useState<string | null>(null),
    [history, setHistory] = useState<any[]>([]),
    [pulse, setPulse] = useState(0),
    [open, setOpen] = useState(false),
    [busy, setBusy] = useState(false),
    [sources, setSources] = useState<any[]>([]),
    [memoryIds, setMemoryIds] = useState<string[]>([]),
    [toolEvents, setToolEvents] = useState<any[]>([]);
  const saveQueue = useRef(Promise.resolve()),
    abort = useRef<AbortController | null>(null),
    bottom = useRef<HTMLDivElement>(null),
    location = useLocation(),
    navigate = useNavigate();
  const [historyOpen, setHistoryOpen] = useState(false);
  const historyDialog = useRef<HTMLDialogElement>(null);
  const area = areaFor(location.pathname);
  useEffect(() => {
    const dialog = historyDialog.current;
    if (!dialog) return;
    if (historyOpen && !dialog.open) dialog.showModal();
    else if (!historyOpen && dialog.open) dialog.close();
  }, [historyOpen]);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const voiceActive = useRef(false),
    voiceStarting = useRef(false),
    voiceUntil = useRef(0),
    sendVoice = useRef<(text: string) => void>(() => {});
  const audio = useAudio(setState, setError, setInput, () =>
    setPulse(performance.now()),
  );
  function disableVoice() {
    voiceActive.current = false;
    voiceUntil.current = 0;
    setVoiceEnabled(false);
    audio.stopMic();
  }
  function listenVoice() {
    if (!voiceActive.current || document.hidden || voiceStarting.current)
      return;
    voiceStarting.current = true;
    void audio
      .startMic(false, (text) => {
        if (!voiceActive.current) return;
        const result = voiceCommand(text, Date.now(), voiceUntil.current);
        if (!result) return;
        if (result.activated) voiceUntil.current = Date.now() + 30000;
        if (!result.command) {
          setInput("");
          return;
        }
        if (
          /^(desligar microfone|desligue o microfone|sair do modo de voz|silenciar)$/i.test(
            result.command,
          )
        ) {
          disableVoice();
          audio.stopSpeech();
          return;
        }
        audio.stopMic();
        setInput(result.command);
        sendVoice.current(result.command);
      })
      .finally(() => {
        voiceStarting.current = false;
      });
  }
  sendVoice.current = (text) => {
    void send({ preventDefault: () => {} } as React.FormEvent, text);
  };
  useEffect(() => {
    if (state === "error" && voiceActive.current) {
      disableVoice();
      return;
    }
    if (voiceEnabled && !audio.listening && !busy && state === "idle") {
      const timer = setTimeout(listenVoice, 250);
      return () => clearTimeout(timer);
    }
  }, [voiceEnabled, audio.listening, busy, state]);
  useEffect(() => {
    const hide = () => {
      if (document.hidden && voiceActive.current) {
        disableVoice();
        audio.stopSpeech();
      }
    };
    document.addEventListener("visibilitychange", hide);
    return () => document.removeEventListener("visibilitychange", hide);
  }, []);
  useEffect(() => {
    api("/auth/me")
      .then(() => setAuth(true))
      .catch(() => setAuth(false));
  }, []);
  const refreshHistory = () =>
    api("/conversations")
      .then(setHistory)
      .catch((e) => setError(e.message));
  useEffect(() => {
    if (!auth) return;
    api("/settings")
      .then(setPrefs)
      .catch((e) => setError(e.message));
    void refreshHistory();
    const check = () =>
      !document.hidden &&
      api(
        "/health" +
          (conversation
            ? "?conversation_id=" + encodeURIComponent(conversation)
            : ""),
      )
        .then(setHealth)
        .catch(() => setHealth(null));
    void check();
    const timer = setInterval(check, 15000);
    window.addEventListener("saly-model-changed", check);
    return () => {
      clearInterval(timer);
      window.removeEventListener("saly-model-changed", check);
    };
  }, [auth, conversation]);
  useEffect(() => {
    bottom.current?.scrollIntoView({
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
    });
  }, [messages]);
  useEffect(() => {
    setOpen(false);
    setHistoryOpen(false);
    disableVoice();
    audio.stopSpeech();
    audio.stopMic();
    abort.current?.abort();
  }, [location.pathname]);
  useEffect(() => {
    const request = location.state?.salyBookDraft;
    if (typeof request === "string") setInput(request.slice(0, 12000));
  }, [location.key]);
  async function save(p: Prefs) {
    setPrefs(p);
    try {
      saveQueue.current = saveQueue.current
        .catch(() => {})
        .then(() => put("/settings", p))
        .then(() => {});
      await saveQueue.current;
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function send(e: React.FormEvent, forced?: string) {
    e.preventDefault();
    const draft = forced ?? input;
    if (!draft.trim() || busy) return;
    if (health?.provider !== "ollama" && !prefs?.privacy.remoteConsent) {
      if (
        !prefs ||
        !confirm(
          "Enviar esta mensagem e o contexto autorizado ao provedor remoto configurado? Você pode revogar essa autorização em Privacidade.",
        )
      )
        return;
      try {
        const next = {
          ...prefs,
          privacy: { ...prefs.privacy, remoteConsent: true },
        };
        await put("/settings", next);
        setPrefs(next);
      } catch (e) {
        setError((e as Error).message);
        return;
      }
    }
    audio.stopMic();
    audio.stopSpeech();
    setError("");
    setBusy(true);
    setSources([]);
    setMemoryIds([]);
    setToolEvents([]);
    setState("thinking");
    const text = draft.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    const controller = new AbortController();
    abort.current = controller;
    let currentSources: any[] = [];
    let answer = "",
      begun = false,
      completed = false;
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, conversation_id: conversation }),
        signal: controller.signal,
      });
      if (!response.ok) {
        const d = await response.json();
        throw Error(d.detail || "Falha no chat");
      }
      if (!response.body) throw Error("Streaming indisponível");
      const reader = response.body.getReader(),
        decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        let idx;
        while ((idx = buffer.indexOf("\n")) >= 0) {
          const line = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 1);
          if (!line.trim()) continue;
          const event = JSON.parse(line);
          if (event.type === "context") {
            setConversation(event.conversation_id);
            setSources(event.sources);
            currentSources = event.sources;
            setMemoryIds(event.memory_ids);
          }
          if (event.type === "state") setState(event.state);
          if (event.type === "tool")
            setToolEvents((items) => [...items, event]);
          if (event.type === "tool" && event.result.approval_required)
            setError(
              "Uma operação está aguardando sua revisão no painel de aprovações.",
            );
          if (event.type === "token") {
            if (!begun) {
              begun = true;
              setState("responding");
              setPulse(performance.now());
              setMessages((m) => [...m, { role: "assistant", content: "" }]);
            }
            answer += event.text;
            setMessages((m) => [
              ...m.slice(0, -1),
              { role: "assistant", content: answer, partial: true },
            ]);
          }
          if (event.type === "error") throw Error(event.detail);
          if (event.type === "done") {
            completed = true;
            answer = event.content ?? answer;
            setMessages((m) => [
              ...(begun ? m.slice(0, -1) : m),
              {
                role: "assistant",
                content: answer,
                sources: currentSources,
                verification: event.verification,
                model: event.model,
                provider: event.provider,
              },
            ]);
            begun = true;
          }
        }
        if (done) break;
      }
      if (!completed) throw Error("Fluxo encerrado antes da conclusão.");
      emit({ type: "MODEL_RESPONSE_COMPLETED", id: "interaction" });
      if (voiceActive.current && answer && prefs)
        audio.speak(answer, prefs.voice, () => {
          voiceUntil.current = Date.now() + 30000;
        });
      else if (prefs?.voice.autoSpeak && answer)
        audio.speak(answer, prefs.voice);
    } catch (e) {
      if (voiceActive.current) disableVoice();
      if ((e as Error).name === "AbortError") {
        setState("idle");
        setError(
          "Geração interrompida. Trechos parciais não são salvos como resposta concluída.",
        );
      } else {
        setError((e as Error).message);
        setState("error");
      }
    } finally {
      abort.current = null;
      setBusy(false);
      void refreshHistory();
    }
  }
  function stop() {
    disableVoice();
    abort.current?.abort();
    audio.stopMic();
    audio.stopSpeech();
    setState("idle");
  }
  async function teach(content: string) {
    const correction = prompt(
      "Revise a informação antes de autorizar seu armazenamento:",
      content,
    );
    if (!correction?.trim()) return;
    try {
      await post("/memories", {
        content: correction,
        category: "semantica",
        source: "conversa aprovada pelo usuário",
      });
      setError("Memória registrada como não verificada. Revise em Memórias.");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (auth === null)
    return (
      <div className="loading">
        Conectando ao seu espaço…{" "}
        <NavLink to="/offline">Abrir cofre local</NavLink>
      </div>
    );
  if (!auth) return <Login done={() => setAuth(true)} />;
  const navigation = [
    ["/", "Conversa", MessageCircle, "conversation"],
    ["/knowledge", "Conhecimento", Leaf, "knowledge"],
    ["/studio", "Mídia", Film, "media"],
    ["/routine", "Rotina", CalendarDays, "routine"],
  ] as const;
  return (
    <div
      className={`app saly-two area-${area} ${messages.length ? "has-conversation" : ""}`}
    >
      <a className="skip" href="#main">
        Pular para conteúdo
      </a>
      <aside className={open ? "sidebar open" : "sidebar"}>
        <NavLink to="/" className="brand">
          <div className="brand-symbol">S</div>
          <div>
            SALY<small>INTELLIGENCE</small>
          </div>
        </NavLink>
        <nav aria-label="Áreas principais">
          {navigation.map(([to, label, Icon, key]) => (
            <NavLink
              key={to}
              to={to}
              end
              className={area === key ? "active" : ""}
              aria-current={area === key ? "page" : undefined}
            >
              <Icon size={22} strokeWidth={1.35} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="rail-utilities">
          <NavLink to="/advanced" aria-label="Ajustes e recursos">
            <Settings size={20} />
            <span>Ajustes</span>
          </NavLink>
          <button
            aria-label="Sair"
            onClick={async () => {
              try {
                stop();
                await post("/auth/logout");
                setAuth(false);
                setMessages([]);
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            <LogOut size={19} />
            <span>Sair</span>
          </button>
        </div>
      </aside>
      <dialog
        ref={historyDialog}
        className="history-drawer"
        aria-label="Histórico de conversas"
        onCancel={() => setHistoryOpen(false)}
      >
        <div className="drawer-heading">
          <span>Suas conversas</span>
          <button
            className="icon-button"
            aria-label="Fechar histórico"
            onClick={() => setHistoryOpen(false)}
          >
            <X size={20} />
          </button>
        </div>
        <div className="history-title">
          CONVERSAS{" "}
          <button
            aria-label="Nova conversa"
            disabled={busy}
            onClick={() => {
              stop();
              setConversation(null);
              setMessages([]);
              setSources([]);
              setMemoryIds([]);
            }}
          >
            <Plus size={16} />
          </button>
        </div>
        <input
          className="history-search"
          aria-label="Pesquisar conversas"
          placeholder="Buscar conversas…"
          value={historyQuery}
          onChange={(e) => setHistoryQuery(e.target.value)}
        />
        <div className="history">
          {history
            .filter((h) =>
              h.title
                .toLocaleLowerCase()
                .includes(historyQuery.toLocaleLowerCase()),
            )
            .map((h) => (
              <button
                key={h.id}
                disabled={busy}
                className={h.id === conversation ? "selected" : ""}
                onClick={async () => {
                  try {
                    stop();
                    setMessages(await api("/conversations/" + h.id));
                    setConversation(h.id);
                    setHistoryOpen(false);
                    navigate("/");
                    setSources([]);
                    setMemoryIds([]);
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                {h.title}
              </button>
            ))}
          {!history.length && <small>Suas conversas aparecerão aqui.</small>}
        </div>
      </dialog>
      {open && (
        <button
          className="overlay"
          aria-label="Fechar menu"
          onClick={() => setOpen(false)}
        />
      )}
      <nav className="mobile-areas" aria-label="Navegação móvel">
        {navigation.map(([to, label, Icon, key]) => (
          <NavLink
            key={to}
            end
            to={to}
            className={area === key ? "active" : ""}
            aria-current={area === key ? "page" : undefined}
          >
            <Icon size={21} strokeWidth={1.5} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="main-shell">
        <header className="topbar">
          <button
            className="icon-button menu-toggle"
            aria-label="Alternar menu"
            onClick={() => setOpen(!open)}
          >
            <Menu size={20} />
          </button>
          <span className="area-breadcrumb">
            <Leaf size={15} />
            {areaLabels[area]}
          </span>
          <div className="topbar-actions">
            <span
              className={`connection-label ${health?.model_ready ? "online" : ""}`}
            >
              <i />
              {health?.model_ready ? "Modelo conectado" : "Modelo indisponível"}
            </span>
            <button
              className="icon-button"
              aria-label="Histórico de conversas"
              onClick={() => setHistoryOpen(true)}
            >
              <History size={19} />
            </button>
            <button
              className="icon-button"
              aria-label="Nova conversa"
              disabled={busy}
              onClick={() => {
                stop();
                setConversation(null);
                setMessages([]);
                setSources([]);
                setMemoryIds([]);
                navigate("/");
              }}
            >
              <Plus size={20} />
            </button>
          </div>
        </header>
        {areaLinks[area] && (
          <nav
            className="area-tabs"
            aria-label={`Navegação de ${areaLabels[area]}`}
          >
            {areaLinks[area].map((item) => (
              <NavLink end key={item.to} to={item.to}>
                {item.name}
              </NavLink>
            ))}
          </nav>
        )}
        <main id="main">
          <PwaUpdate />
          <AlarmNotifier
            enabled={prefs?.notifications?.enabled ?? false}
            speak={(text) => {
              if (prefs) audio.speak(text, prefs.voice);
            }}
            stop={audio.stopSpeech}
          />
          <ReminderAlerts
            enabled={prefs?.notifications?.enabled ?? false}
            quietStart={prefs?.notifications?.quietStart}
            quietEnd={prefs?.notifications?.quietEnd}
            timezone={prefs?.notifications?.timezone}
            minimumImportance={prefs?.notifications?.minimumImportance}
          />
          {error && (
            <div className="notice" role="alert">
              <span>{error}</span>
              <button aria-label="Fechar aviso" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          <Routes>
            <Route
              path="/"
              element={
                <>
                  <section className="hero">
                    <div className="hero-copy">
                      <h1>
                        Olá. Eu sou <em>Saly.</em>
                      </h1>
                      <p>Um espaço para suas ideias crescerem.</p>
                    </div>
                    <div className="hero-status">
                      <span className={`status ${state}`}>
                        <i />
                        {labels[state]}
                      </span>
                    </div>
                    <Suspense
                      fallback={
                        <div className="core-loading">
                          Preparando núcleo visual…
                        </div>
                      }
                    >
                      <Core
                        state={state}
                        level={audio.level}
                        speechSignal={audio.speechSignal}
                        quality={prefs?.graphics || "auto"}
                        pulse={pulse}
                      />
                    </Suspense>
                  </section>
                  <section
                    className="conversation"
                    aria-label="Conversa com Saly"
                  >
                    <LocalModels
                      conversation={conversation}
                      busy={busy}
                      notify={setError}
                      changed={() => {
                        void api(
                          "/health" +
                            (conversation
                              ? "?conversation_id=" +
                                encodeURIComponent(conversation)
                              : ""),
                        ).then(setHealth);
                      }}
                    />
                    <div className="messages" aria-live="polite">
                      {messages.map((m, i) => (
                        <article className={`message ${m.role}`} key={i}>
                          <span className="avatar">
                            {m.role === "user" ? "EU" : "S"}
                          </span>
                          <div>
                            <small>
                              {m.role === "user" ? "VOCÊ" : "SALY"}{" "}
                              {m.partial ? "· PARCIAL" : ""}{" "}
                              {m.model
                                ? `· ${m.provider || ""} / ${m.model}`
                                : ""}
                            </small>
                            <div className="markdown">
                              <Markdown
                                remarkPlugins={[remarkGfm]}
                                skipHtml
                                components={{
                                  img: ({ src, alt }) => (
                                    <a
                                      href={src}
                                      target="_blank"
                                      rel="noreferrer noopener"
                                    >
                                      Imagem externa: {alt || "abrir"}{" "}
                                      (carregamento automático desativado)
                                    </a>
                                  ),
                                  a: ({ children, ...props }) => (
                                    <a
                                      {...props}
                                      target="_blank"
                                      rel="noreferrer noopener"
                                    >
                                      {children}
                                    </a>
                                  ),
                                }}
                              >
                                {m.content}
                              </Markdown>
                            </div>
                            {m.sources?.map((source: any) => (
                              <a
                                className="citation"
                                key={source.chunk_id}
                                href={source.url}
                                target="_blank"
                                rel="noreferrer"
                              >
                                {source.name} ·{" "}
                                {typeof source.start_seconds === "number"
                                  ? `${source.start_seconds.toFixed(2)}s`
                                  : source.page
                                    ? `p. ${source.page}`
                                    : "legado sem página"}{" "}
                                · trecho {source.position + 1} ↗
                              </a>
                            ))}
                            {m.verification && (
                              <VerificationDetails
                                verification={m.verification}
                              />
                            )}
                            {m.role === "assistant" && !m.partial && (
                              <div className="toolbar">
                                <button
                                  className="text-button"
                                  disabled={!prefs}
                                  onClick={() =>
                                    prefs && audio.speak(m.content, prefs.voice)
                                  }
                                >
                                  <Volume2 size={14} /> Ouvir
                                </button>
                                <button
                                  className="text-button"
                                  onClick={() =>
                                    void navigator.clipboard
                                      .writeText(m.content)
                                      .catch(() =>
                                        setError(
                                          "Não foi possível copiar a resposta.",
                                        ),
                                      )
                                  }
                                >
                                  Copiar
                                </button>
                                <button
                                  className="text-button"
                                  disabled={busy}
                                  onClick={() => {
                                    const last = [...messages.slice(0, i)]
                                      .reverse()
                                      .find((m) => m.role === "user");
                                    if (last)
                                      void send(
                                        {
                                          preventDefault: () => {},
                                        } as React.FormEvent,
                                        last.content,
                                      );
                                  }}
                                >
                                  Regenerar
                                </button>
                                <button
                                  className="text-button"
                                  onClick={() => void teach(m.content)}
                                >
                                  Propor memória
                                </button>
                              </div>
                            )}
                          </div>
                        </article>
                      ))}
                      {busy && (
                        <div className="stream-status" role="status">
                          {state === "thinking"
                            ? "Aguardando o provedor remoto…"
                            : "Recebendo resposta…"}
                        </div>
                      )}
                      <div ref={bottom} />
                    </div>
                    {(sources.length > 0 || memoryIds.length > 0) && (
                      <details className="sources">
                        <summary>
                          Contexto recuperado: {sources.length} trechos ·{" "}
                          {memoryIds.length} memórias autorizadas
                        </summary>
                        {sources.map((s, i) => (
                          <p key={i}>
                            <a href={s.url} target="_blank" rel="noreferrer">
                              {s.name} ·{" "}
                              {typeof s.start_seconds === "number"
                                ? `${s.start_seconds.toFixed(2)}s`
                                : s.page
                                  ? `página ${s.page}`
                                  : "página não disponível"}{" "}
                              · trecho {s.position + 1}
                            </a>
                            : {s.content.slice(0, 200)}
                          </p>
                        ))}
                        {memoryIds.map((id) => (
                          <p key={id}>Memória {id}</p>
                        ))}
                        <small>
                          Fontes recuperadas não garantem que cada afirmação
                          esteja fundamentada.
                        </small>
                      </details>
                    )}
                    {toolEvents.length > 0 && (
                      <details className="sources">
                        <summary>
                          Consultas e operações desta resposta (
                          {toolEvents.length})
                        </summary>
                        {toolEvents.map((event, i) => (
                          <div key={i}>
                            <strong>{event.tool}</strong>
                            <p>
                              {event.result.approval_required
                                ? "Aguardando aprovação — não executada"
                                : event.result.executed
                                  ? "Resultado recebido e registrado"
                                  : "Não foi possível confirmar"}
                            </p>
                            <pre className="tool-result">
                              {JSON.stringify(event.result, null, 2)}
                            </pre>
                          </div>
                        ))}
                      </details>
                    )}
                    <form className="composer" onSubmit={send}>
                      <textarea
                        rows={2}
                        aria-label="Mensagem para Saly"
                        value={input}
                        maxLength={12000}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Compartilhe uma ideia com Saly…"
                        onKeyDown={(e) => {
                          if (
                            e.key === "Enter" &&
                            !e.shiftKey &&
                            !e.nativeEvent.isComposing
                          ) {
                            e.preventDefault();
                            e.currentTarget.form?.requestSubmit();
                          }
                        }}
                      />
                      <div className="composer-bottom">
                        <div>
                          <button
                            type="button"
                            disabled={busy && !voiceEnabled}
                            aria-pressed={voiceEnabled}
                            onClick={() => {
                              if (voiceActive.current) {
                                disableVoice();
                                audio.stopSpeech();
                                return;
                              }
                              if (
                                health?.provider !== "ollama" &&
                                !prefs?.privacy.remoteConsent
                              ) {
                                setError(
                                  "Autorize o provedor remoto em Privacidade antes do modo de voz.",
                                );
                                return;
                              }
                              if (
                                !confirm(
                                  "Ativar voz enquanto esta página estiver aberta? O reconhecimento do navegador pode enviar áudio ao fornecedor. Diga SALY e o comando; depois há uma janela de 30 segundos para continuar. A voz usada será a selecionada no catálogo.",
                                )
                              )
                                return;
                              voiceActive.current = true;
                              voiceUntil.current = 0;
                              setVoiceEnabled(true);
                              listenVoice();
                            }}
                          >
                            {voiceEnabled
                              ? "Desligar modo de voz"
                              : "Modo de voz SALY"}
                          </button>
                          <button
                            type="button"
                            className={audio.listening ? "mic active" : "mic"}
                            disabled={busy || voiceEnabled}
                            aria-label={
                              audio.listening
                                ? "Parar microfone"
                                : "Ativar microfone"
                            }
                            aria-pressed={audio.listening}
                            onClick={() =>
                              audio.listening
                                ? audio.stopMic()
                                : void audio.startMic(
                                    prefs?.privacy.wakeWordEnabled,
                                  )
                            }
                          >
                            <Mic size={17} />
                            {audio.listening ? "Encerrar" : "Microfone"}
                          </button>
                          <details className="mic-options">
                            <summary>Mais opções de voz</summary>
                            <button
                              type="button"
                              className="text-button push-talk"
                              disabled={busy || voiceEnabled}
                              onPointerDown={(e) => {
                                e.currentTarget.setPointerCapture(e.pointerId);
                                void audio.startMic();
                              }}
                              onPointerUp={() => audio.stopMic()}
                              onPointerCancel={() => audio.stopMic()}
                              onKeyDown={(e) => {
                                if (e.code === "Space" && !e.repeat) {
                                  e.preventDefault();
                                  void audio.startMic();
                                }
                              }}
                              onKeyUp={(e) => {
                                if (e.code === "Space") audio.stopMic();
                              }}
                            >
                              Segure para falar
                            </button>
                          </details>
                          {(busy ||
                            audio.listening ||
                            state === "speaking" ||
                            state === "synthesizing" ||
                            state === "paused") && (
                            <button
                              type="button"
                              className="text-button"
                              onClick={stop}
                            >
                              <Square size={14} />
                              Interromper
                            </button>
                          )}
                          {state === "speaking" && (
                            <button
                              type="button"
                              className="text-button"
                              onClick={audio.pause}
                            >
                              <Pause size={14} />
                              Pausar
                            </button>
                          )}
                          {state === "paused" && (
                            <button
                              type="button"
                              className="text-button"
                              onClick={audio.resume}
                            >
                              <Play size={14} />
                              Retomar
                            </button>
                          )}
                        </div>
                        <button
                          className="send"
                          disabled={
                            busy || !input.trim() || !health?.model_ready
                          }
                          aria-label="Enviar mensagem"
                        >
                          <Send size={17} />
                        </button>
                      </div>
                    </form>
                    {!messages.length && (
                      <div className="conversation-context">
                        <NavLink to="/knowledge/documents">
                          <BookOpen size={15} />
                          Explorar um documento
                        </NavLink>
                        <NavLink to="/routine">
                          <CalendarDays size={15} />
                          Organizar meu dia
                        </NavLink>
                      </div>
                    )}
                    <div className="composer-note">
                      {!health?.model_ready
                        ? "O modelo ainda não está disponível. Memórias e documentos continuam acessíveis."
                        : "Saly pode errar. Verifique informações importantes."}{" "}
                      · Voz do navegador pode usar serviços externos.{" "}
                      {voiceEnabled && (
                        <span role="status">
                          Modo de voz ativo: diga SALY. Microfone{" "}
                          {audio.listening
                            ? "ouvindo"
                            : "desligado durante processamento/resposta"}
                          . Ao ocultar a página, o modo é desligado.
                        </span>
                      )}
                    </div>
                  </section>
                  <Approvals notify={setError} compact />
                </>
              }
            />
            <Route
              path="/routine"
              element={
                <Suspense fallback={<p>Preparando sua rotina…</p>}>
                  <RoutineHome />
                </Suspense>
              }
            />
            <Route
              path="/advanced"
              element={
                <Suspense fallback={<p>Preparando ajustes…</p>}>
                  <AdvancedHome />
                </Suspense>
              }
            />
            <Route
              path="/advanced/media"
              element={
                <Suspense fallback={<p>Consultando provedores…</p>}>
                  <MediaAdvanced />
                </Suspense>
              }
            />
            <Route path="/media" element={<Navigate to="/studio" replace />} />
            <Route
              path="/knowledge"
              element={
                <Suspense fallback={<p>Abrindo seu conhecimento…</p>}>
                  <KnowledgeHome />
                </Suspense>
              }
            />
            <Route path="/memory" element={<Memories notify={setError} />} />
            <Route
              path="/knowledge/:documentId/text"
              element={
                <Suspense fallback={<p>Abrindo livro…</p>}>
                  <TextBook />
                </Suspense>
              }
            />
            <Route
              path="/knowledge/:documentId/read"
              element={
                <Suspense fallback={<p>Carregando leitor PDF…</p>}>
                  <PdfBook />
                </Suspense>
              }
            />
            <Route
              path="/knowledge/documents"
              element={
                <Smolin
                  notify={setError}
                  collectionName={prefs?.collectionName || "Smoln"}
                />
              }
            />
            <Route
              path="/voices"
              element={
                prefs && (
                  <Voices
                    prefs={prefs}
                    save={save}
                    voices={audio.voices}
                    speak={(s) => audio.speak(s, prefs.voice)}
                    preview={(uri, text) =>
                      audio.speak(text, { ...prefs.voice, voiceURI: uri })
                    }
                    stop={audio.stopSpeech}
                    pause={audio.pause}
                    resume={audio.resume}
                    speechState={state}
                  />
                )
              }
            />
            <Route
              path="/agenda"
              element={
                <Suspense fallback={<p>Carregando agenda…</p>}>
                  <PlanningPage
                    notify={setError}
                    timezone={prefs?.notifications?.timezone}
                  />
                </Suspense>
              }
            />
            <Route
              path="/alarms"
              element={
                prefs && (
                  <Suspense fallback={<p>Carregando alarmes…</p>}>
                    <AlarmsPage prefs={prefs} save={save} notify={setError} />
                  </Suspense>
                )
              }
            />
            <Route
              path="/purchases"
              element={
                <Suspense fallback={<p>Carregando compras…</p>}>
                  <Purchases notify={setError} />
                </Suspense>
              }
            />
            <Route
              path="/space"
              element={
                <Suspense fallback={<p>Carregando espaço…</p>}>
                  <Space notify={setError} />
                </Suspense>
              }
            />
            <Route
              path="/library"
              element={
                <Suspense fallback={<p>Carregando biblioteca…</p>}>
                  <Library
                    notify={setError}
                    speak={(text) => prefs && audio.speak(text, prefs.voice)}
                    stop={audio.stopSpeech}
                    pause={audio.pause}
                    resume={audio.resume}
                    speechState={state}
                  />
                </Suspense>
              }
            />
            <Route
              path="/studio"
              element={
                <Suspense fallback={<p>Carregando estúdio…</p>}>
                  <Studio notify={setError} />
                </Suspense>
              }
            />
            <Route
              path="/laboratory"
              element={<Laboratory notify={setError} />}
            />
            <Route path="/tools" element={<Tools notify={setError} />} />
            <Route path="/activity" element={<Activity notify={setError} />} />
            <Route
              path="/evaluation"
              element={<Evaluation notify={setError} />}
            />
            {["", "personality", "privacy", "system"].map((section) => (
              <Route
                key={section}
                path={"/settings" + (section ? "/" + section : "")}
                element={
                  prefs && (
                    <>
                      <div className="settings-nav">
                        {["", "personality", "privacy", "system"].map(
                          (p, i) => (
                            <NavLink
                              key={p}
                              end
                              to={"/settings" + (p ? "/" + p : "")}
                            >
                              {
                                [
                                  "Geral",
                                  "Personalidade",
                                  "Privacidade",
                                  "Sistema",
                                ][i]
                              }
                            </NavLink>
                          ),
                        )}
                      </div>
                      <SettingsPanel
                        section={section}
                        prefs={prefs}
                        save={save}
                        health={health}
                        notify={setError}
                      />
                    </>
                  )
                }
              />
            ))}
            <Route
              path="*"
              element={
                <div className="empty">
                  Página não encontrada.{" "}
                  <NavLink to="/">Voltar para Saly</NavLink>
                </div>
              }
            />
          </Routes>
        </main>
        <footer className="site-footer">
          <span>SALY</span>
          <NavLink to="/offline">Cofre local</NavLink>
          <NavLink to="/advanced">Ajustes e privacidade</NavLink>
        </footer>
      </div>
    </div>
  );
}
function AppEntry() {
  const location = useLocation();
  return location.pathname === "/offline" ? (
    <Suspense fallback={<div className="loading">Abrindo cofre local…</div>}>
      <OfflineWorkspace />
    </Suspense>
  ) : (
    <App />
  );
}
createRoot(document.getElementById("root")!).render(
  <BrowserRouter>
    <AppEntry />
  </BrowserRouter>,
);
