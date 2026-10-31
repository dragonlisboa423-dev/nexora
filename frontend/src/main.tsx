import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  NavLink,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import {
  Activity as ActivityIcon,
  AudioLines,
  Brain,
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
import {
  Activity,
  Evaluation,
  Knowledge,
  Memories,
  SettingsPanel,
  Voices,
} from "./Panels";
import "./style.css";
const labels: Record<SalyState, string> = {
  idle: "Em repouso",
  listening: "Escutando",
  thinking: "Gerando resposta",
  responding: "Respondendo",
  speaking: "Falando",
  paused: "Fala pausada",
  executing: "Executando operação",
  error: "Atenção necessária",
};
type Message = { role: string; content: string; partial?: boolean };
function Login({ done }: { done: () => void }) {
  const [setup, setSetup] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    api("/bootstrap")
      .then((d) => setSetup(d.needs_setup))
      .catch((e) => setError(e.message));
  }, []);
  return (
    <div className="login">
      <div className="login-mark">S</div>
      <small>SALY INTELLIGENCE</small>
      <h1>Seu espaço de inteligência.</h1>
      <p>
        Memória, contexto e possibilidades.
        <br />
        Sob seu controle.
      </p>
      <form
        className="card"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          const data = new FormData(e.currentTarget);
          try {
            await post(
              "/auth/" + (setup ? "register" : "login"),
              Object.fromEntries(data),
            );
            done();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <h2>{setup ? "Criar conta proprietária" : "Bem-vindo de volta"}</h2>
        {setup && (
          <p>Mantenha as portas privadas durante o cadastro inicial.</p>
        )}
        <label>
          Usuário
          <input
            autoComplete="username"
            name="username"
            pattern="[\w.@-]+"
            required
            minLength={3}
          />
        </label>
        <label>
          Senha (mínimo 12 caracteres)
          <input
            type="password"
            autoComplete={setup ? "new-password" : "current-password"}
            name="password"
            required
            minLength={12}
          />
        </label>
        {error && <p role="alert">{error}</p>}
        <button disabled={busy}>
          {busy ? "Aguarde…" : setup ? "Criar meu espaço" : "Entrar"}
        </button>
      </form>
      <small>
        Inferência local · Dados privados · Sem API comercial obrigatória
      </small>
    </div>
  );
}
function App() {
  const [auth, setAuth] = useState<boolean | null>(null),
    [prefs, setPrefs] = useState<Prefs | null>(null),
    [health, setHealth] = useState<any>(null),
    [state, setState] = useState<SalyState>("idle"),
    [error, setError] = useState(""),
    [input, setInput] = useState(""),
    [messages, setMessages] = useState<Message[]>([]),
    [conversation, setConversation] = useState<string | null>(null),
    [history, setHistory] = useState<any[]>([]),
    [pulse, setPulse] = useState(0),
    [open, setOpen] = useState(false),
    [busy, setBusy] = useState(false),
    [sources, setSources] = useState<any[]>([]),
    [memoryIds, setMemoryIds] = useState<string[]>([]);
  const saveQueue = useRef(Promise.resolve()),
    abort = useRef<AbortController | null>(null),
    bottom = useRef<HTMLDivElement>(null),
    location = useLocation();
  const audio = useAudio(setState, setError, setInput, () =>
    setPulse(performance.now()),
  );
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
      api("/health")
        .then(setHealth)
        .catch(() => setHealth(null));
    void check();
    const timer = setInterval(check, 15000);
    return () => clearInterval(timer);
  }, [auth]);
  useEffect(() => {
    bottom.current?.scrollIntoView({
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
    });
  }, [messages]);
  useEffect(() => {
    setOpen(false);
    audio.stopSpeech();
    audio.stopMic();
    abort.current?.abort();
  }, [location.pathname]);
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
  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || busy) return;
    audio.stopMic();
    audio.stopSpeech();
    setError("");
    setBusy(true);
    setSources([]);
    setMemoryIds([]);
    setState("thinking");
    const text = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    const controller = new AbortController();
    abort.current = controller;
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
            setMemoryIds(event.memory_ids);
          }
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
            setMessages((m) => [
              ...m.slice(0, -1),
              { role: "assistant", content: answer },
            ]);
          }
        }
        if (done) break;
      }
      if (!completed) throw Error("Fluxo encerrado antes da conclusão.");
      setState("idle");
      if (prefs?.voice.autoSpeak && answer) audio.speak(answer, prefs.voice);
    } catch (e) {
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
    return <div className="loading">Conectando ao seu espaço…</div>;
  if (!auth) return <Login done={() => setAuth(true)} />;
  const navigation = [
    ["/", "Visão central", Sparkles],
    ["/memory", "Memórias", Brain],
    ["/knowledge", "Conhecimentos", Database],
    ["/voices", "Biblioteca de vozes", AudioLines],
    ["/activity", "Atividades", ActivityIcon],
    ["/evaluation", "Avaliação", ShieldCheck],
    ["/settings", "Configurações", Settings],
  ] as const;
  return (
    <div className="app">
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
        <div className="workspace-label">SEU ESPAÇO PESSOAL</div>
        <nav>
          {navigation.map(([to, label, Icon]) => (
            <NavLink to={to} end={to === "/"} key={to}>
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
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
        <div className="history">
          {history.map((h) => (
            <button
              key={h.id}
              disabled={busy}
              className={h.id === conversation ? "selected" : ""}
              onClick={async () => {
                try {
                  stop();
                  setMessages(await api("/conversations/" + h.id));
                  setConversation(h.id);
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
        <div className="sidebar-footer">
          <span className={`dot ${health?.model_ready ? "online" : ""}`} />
          <div>
            {health?.model_ready ? "Modelo conectado" : "Modelo desconectado"}
            <small>{health?.model || "Verificando conexão"}</small>
          </div>
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
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      {open && (
        <button
          className="overlay"
          aria-label="Fechar menu"
          onClick={() => setOpen(false)}
        />
      )}
      <div className="main-shell">
        <header className="topbar">
          <button
            className="icon-button"
            aria-label="Alternar menu"
            onClick={() => setOpen(!open)}
          >
            <Menu size={20} />
          </button>
          <span>
            Workspace <ChevronRight size={13} />{" "}
            {navigation.find(([p]) => p === location.pathname)?.[1] ||
              "Configurações"}
          </span>
          <div>
            <span className={`dot ${health?.model_ready ? "online" : ""}`} />
            {health?.model_ready
              ? "Inferência disponível"
              : "Inferência indisponível"}
            <span className="private">
              <ShieldCheck size={14} /> Espaço privado
            </span>
          </div>
        </header>
        <main id="main">
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
                      <div className="eyebrow">
                        <span />
                        INTELIGÊNCIA QUE CONSTRÓI CONTEXTO
                      </div>
                      <h1>
                        Olá. Eu sou <em>Saly.</em>
                      </h1>
                      <p>
                        Um espaço para pensar, aprender e criar.
                        <br />
                        Sua inteligência pessoal, com memória e propósito.
                      </p>
                    </div>
                    <div className="hero-status">
                      <span className={`status ${state}`}>
                        <i />
                        {labels[state]}
                      </span>
                      <small>
                        {health?.model_ready
                          ? "MODELO LOCAL · CPU COMPATÍVEL"
                          : "CONECTE O MODELO PARA CONVERSAR"}
                      </small>
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
                        quality={prefs?.graphics || "auto"}
                        pulse={pulse}
                      />
                    </Suspense>
                    <div className="core-footnote">
                      <span>MEMÓRIA PERSISTENTE</span>
                      <i />
                      <span>CONTEXTO AUTORIZADO</span>
                      <i />
                      <span>CONTROLE HUMANO</span>
                    </div>
                  </section>
                  <section
                    className="conversation"
                    aria-label="Conversa com Saly"
                  >
                    <div className="section-line">
                      <span>CONVERSA</span>
                      <small>
                        {messages.length
                          ? "Contexto da sessão"
                          : "Comece com uma ideia"}
                      </small>
                      <button
                        className="text-button"
                        disabled={busy}
                        onClick={() => {
                          stop();
                          setConversation(null);
                          setMessages([]);
                          setSources([]);
                          setMemoryIds([]);
                        }}
                      >
                        Nova conversa
                      </button>
                    </div>
                    {!messages.length && (
                      <div className="suggestions">
                        {[
                          "Ajude-me a organizar uma ideia",
                          "O que você sabe sobre meu projeto?",
                          "Vamos explorar um novo assunto",
                        ].map((t, i) => (
                          <button key={t} onClick={() => setInput(t)}>
                            <span>0{i + 1}</span>
                            {t}
                            <ChevronRight size={15} />
                          </button>
                        ))}
                      </div>
                    )}
                    <div className="messages" aria-live="polite">
                      {messages.map((m, i) => (
                        <article className={`message ${m.role}`} key={i}>
                          <span className="avatar">
                            {m.role === "user" ? "EU" : "S"}
                          </span>
                          <div>
                            <small>
                              {m.role === "user" ? "VOCÊ" : "SALY"}{" "}
                              {m.partial ? "· PARCIAL" : ""}
                            </small>
                            <p>{m.content}</p>
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
                            ? "Aguardando tokens do modelo local…"
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
                            {s.name} · trecho {s.position + 1}:{" "}
                            {s.content.slice(0, 200)}
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
                            className={audio.listening ? "mic active" : "mic"}
                            disabled={busy}
                            aria-label={
                              audio.listening
                                ? "Parar microfone"
                                : "Ativar microfone"
                            }
                            aria-pressed={audio.listening}
                            onClick={() =>
                              audio.listening
                                ? audio.stopMic()
                                : void audio.startMic()
                            }
                          >
                            <Mic size={17} />
                            {audio.listening ? "Encerrar" : "Microfone"}
                          </button>
                          <button
                            type="button"
                            className="text-button push-talk"
                            disabled={busy}
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
                          {(busy ||
                            audio.listening ||
                            state === "speaking" ||
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
                    <div className="composer-note">
                      {!health?.model_ready
                        ? "Modelo offline. Memórias, documentos e ferramentas continuam disponíveis."
                        : "Saly pode errar. Verifique informações importantes."}{" "}
                      · Voz do navegador pode usar serviços externos.
                    </div>
                  </section>
                </>
              }
            />
            <Route path="/memory" element={<Memories notify={setError} />} />
            <Route
              path="/knowledge"
              element={<Knowledge notify={setError} />}
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
                  />
                )
              }
            />
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
          <span>SALY INTELLIGENCE</span>
          <span>Seu contexto. Sua inteligência.</span>
          <span>v0.1 · LOCAL FIRST</span>
        </footer>
      </div>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>,
);
