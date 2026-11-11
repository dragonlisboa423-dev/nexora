import { useEffect, useState } from "react";
import { api, post, put, download, type Prefs } from "./api";
export function Memories({ notify }: { notify: (s: string) => void }) {
  const [items, setItems] = useState<any[]>([]),
    [q, setQ] = useState(""),
    [category, setCategory] = useState(""),
    [selected, setSelected] = useState<string[]>([]),
    [editing, setEditing] = useState<any>(null),
    [versions, setVersions] = useState<any[]>([]);
  const blank = {
    content: "",
    category: "informacoes",
    tags: [],
    relations: [],
    source: "manual",
    verification: "unverified",
    archived: false,
    enabled: true,
  };
  const load = () =>
    api(`/memories?q=${encodeURIComponent(q)}&category=${category}`)
      .then(setItems)
      .catch((e) => notify(e.message));
  useEffect(() => {
    void load();
  }, [q, category]);
  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await (editing.id
        ? put("/memories/" + editing.id, editing)
        : post("/memories", editing));
      setEditing(null);
      setVersions([]);
      await load();
    } catch (e) {
      notify((e as Error).message);
    }
  }
  async function remove() {
    if (
      !selected.length ||
      !confirm(
        "Excluir permanentemente as memórias selecionadas? Cópias em backups existentes continuarão disponíveis.",
      )
    )
      return;
    try {
      await post("/memories/delete", { ids: selected, confirm: true });
      setSelected([]);
      await load();
    } catch (e) {
      notify((e as Error).message);
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="CONTEXTO PERSISTENTE"
        title="Memórias"
        text="Conhecimento sob seu controle. Armazene, revise e decida o que Saly pode utilizar."
      />
      <div className="toolbar">
        <input
          aria-label="Pesquisar memórias"
          placeholder="Pesquisar em suas memórias…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select
          aria-label="Categoria"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option value="">Todas as categorias</option>
          {categories.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
        <button
          onClick={() => {
            setEditing({ ...blank });
            setVersions([]);
          }}
        >
          + Nova memória
        </button>
      </div>
      <div className="toolbar">
        <button
          className="secondary"
          onClick={async () => {
            try {
              download("saly-memorias.json", await api("/memories-export"));
            } catch (e) {
              notify((e as Error).message);
            }
          }}
        >
          Exportar
        </button>
        <label className="file-button">
          Importar JSON
          <input
            type="file"
            accept=".json"
            onChange={async (e) => {
              try {
                const f = e.target.files?.[0];
                if (!f) return;
                if (f.size > 5_000_000) throw Error("Máximo 5 MB");
                const data = JSON.parse(await f.text());
                await post("/memories-import", { memories: data.memories });
                await load();
              } catch (e) {
                notify((e as Error).message);
              }
              e.target.value = "";
            }}
          />
        </label>
        <button
          className="secondary"
          onClick={async () => {
            try {
              const d = await api("/memory-duplicates");
              notify(
                d.length
                  ? `${d.length} grupos de conteúdo duplicado: ${d.map((g: string[]) => g.map((id) => id.slice(0, 8)).join(", ")).join(" / ")}`
                  : "Nenhuma duplicata exata encontrada.",
              );
            } catch (e) {
              notify((e as Error).message);
            }
          }}
        >
          Localizar duplicatas
        </button>
        <button
          className="secondary"
          disabled={selected.length < 2 || selected.length > 20}
          onClick={async () => {
            const content = prompt(
              "Revise o conteúdo consolidado. Os originais serão arquivados e poderão ser restaurados.",
              items
                .filter((m) => selected.includes(m.id))
                .map((m) => m.content)
                .join("\n\n"),
            );
            if (
              !content?.trim() ||
              !confirm(
                "Criar uma nova memória não verificada e arquivar as selecionadas?",
              )
            )
              return;
            try {
              await post("/memories-consolidate", {
                ids: selected,
                content,
                confirm: true,
              });
              setSelected([]);
              await load();
            } catch (e) {
              notify((e as Error).message);
            }
          }}
        >
          Consolidar seleção
        </button>
        <button
          className="danger"
          disabled={!selected.length}
          onClick={() => void remove()}
        >
          Excluir seleção ({selected.length})
        </button>
      </div>
      {editing && (
        <form className="card editor" onSubmit={save}>
          <h2>{editing.id ? "Editar memória" : "Ensinar algo à Saly"}</h2>
          <label>
            Conteúdo
            <textarea
              required
              maxLength={20000}
              value={editing.content}
              onChange={(e) =>
                setEditing({ ...editing, content: e.target.value })
              }
            />
          </label>
          <div className="form-grid">
            <label>
              Categoria
              <select
                value={editing.category}
                onChange={(e) =>
                  setEditing({ ...editing, category: e.target.value })
                }
              >
                {categories.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label>
              Verificação
              <select
                value={editing.verification}
                onChange={(e) =>
                  setEditing({ ...editing, verification: e.target.value })
                }
              >
                <option value="unverified">Não verificada</option>
                <option value="verified">Verificada pelo usuário</option>
                <option value="contested">Contestada (não recuperar)</option>
              </select>
            </label>
            <label>
              Tags (separadas por vírgula)
              <input
                value={editing.tags.join(",")}
                onChange={(e) =>
                  setEditing({ ...editing, tags: e.target.value.split(",") })
                }
              />
            </label>
            <label>
              Origem
              <input
                value={editing.source}
                onChange={(e) =>
                  setEditing({ ...editing, source: e.target.value })
                }
              />
            </label>
            <label>
              Relações — IDs separados por vírgula
              <input
                value={editing.relations.join(",")}
                onChange={(e) =>
                  setEditing({
                    ...editing,
                    relations: e.target.value
                      .split(",")
                      .map((x) => x.trim())
                      .filter(Boolean),
                  })
                }
              />
            </label>
          </div>
          <label>
            Importância: {editing.importance ?? 0.5}
            <input
              type="range"
              min="0"
              max="1"
              step=".1"
              value={editing.importance ?? 0.5}
              onChange={(e) =>
                setEditing({ ...editing, importance: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Validade opcional (fuso do dispositivo)
            <input
              type="datetime-local"
              value={
                editing.expires_at
                  ? new Date(
                      new Date(editing.expires_at).getTime() -
                        new Date(editing.expires_at).getTimezoneOffset() *
                          60000,
                    )
                      .toISOString()
                      .slice(0, 16)
                  : ""
              }
              onChange={(e) =>
                setEditing({
                  ...editing,
                  expires_at: e.target.value
                    ? new Date(e.target.value).toISOString()
                    : null,
                })
              }
            />
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={editing.enabled}
              onChange={(e) =>
                setEditing({ ...editing, enabled: e.target.checked })
              }
            />
            Autorizar uso no contexto
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={editing.archived}
              onChange={(e) =>
                setEditing({ ...editing, archived: e.target.checked })
              }
            />
            Arquivar
          </label>
          <div className="toolbar">
            <button>Salvar</button>
            <button
              type="button"
              className="secondary"
              onClick={() => setEditing(null)}
            >
              Cancelar
            </button>
            {editing.id && (
              <button
                type="button"
                className="secondary"
                onClick={async () => {
                  try {
                    setVersions(await api(`/memories/${editing.id}/versions`));
                  } catch (e) {
                    notify((e as Error).message);
                  }
                }}
              >
                Histórico
              </button>
            )}
          </div>
          {versions.map((v) => (
            <div key={v.id} className="version">
              <span>
                {new Date(v.created).toLocaleString("pt-BR")} —{" "}
                {JSON.parse(v.snapshot).content.slice(0, 100)}
              </span>
              <button
                type="button"
                onClick={async () => {
                  try {
                    setEditing(
                      await post(`/memories/${editing.id}/restore/${v.id}`),
                    );
                    await load();
                    setVersions([]);
                  } catch (e) {
                    notify((e as Error).message);
                  }
                }}
              >
                Restaurar versão
              </button>
            </div>
          ))}
        </form>
      )}
      <div className="memory-grid">
        {items.map((m) => (
          <article className="card memory" key={m.id}>
            <div className="memory-meta">
              <input
                type="checkbox"
                aria-label={`Selecionar ${m.content.slice(0, 30)}`}
                checked={selected.includes(m.id)}
                onChange={(e) =>
                  setSelected(
                    e.target.checked
                      ? [...selected, m.id]
                      : selected.filter((id) => id !== m.id),
                  )
                }
              />
              <span>{m.category}</span>
              <span>{m.verification}</span>
            </div>
            <p>{m.content}</p>
            <div className="tags">
              {m.tags.filter(Boolean).map((t: string, i: number) => (
                <span key={i}>{t}</span>
              ))}
            </div>
            <small>
              Origem: {m.source} · {new Date(m.updated).toLocaleString("pt-BR")}
              <br />
              {m.archived
                ? "Arquivada"
                : m.enabled
                  ? "Uso autorizado"
                  : "Uso desativado"}{" "}
              · ID: {m.id}
            </small>
            {m.relations.length > 0 && (
              <small>Relações: {m.relations.join(", ")}</small>
            )}
            <button
              className="text-button"
              onClick={() => {
                setEditing({ ...m });
                setVersions([]);
              }}
            >
              Revisar memória →
            </button>
          </article>
        ))}
      </div>
      {!items.length && (
        <Empty text="Nenhuma memória encontrada. Crie uma memória ou aprove uma informação a partir da conversa." />
      )}
    </>
  );
}
export const categories = [
  "informacoes",
  "preferencias",
  "projetos",
  "decisoes",
  "atividades",
  "instrucoes",
  "temporarias",
];
export function PageTitle({
  eyebrow,
  title,
  text,
}: {
  eyebrow: string;
  title: string;
  text: string;
}) {
  return (
    <header className="page-title">
      <small>{eyebrow}</small>
      <h1>{title}</h1>
      <p>{text}</p>
    </header>
  );
}
export function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}
export function Knowledge({ notify }: { notify: (s: string) => void }) {
  const [docs, setDocs] = useState<any[]>([]),
    [q, setQ] = useState(""),
    [results, setResults] = useState<any[]>([]),
    [busy, setBusy] = useState(false);
  const load = () =>
    api("/knowledge")
      .then(setDocs)
      .catch((e) => notify(e.message));
  useEffect(() => {
    void load();
  }, []);
  return (
    <>
      <PageTitle
        eyebrow="FONTES & REFERÊNCIAS"
        title="Base de conhecimentos"
        text="Importe PDF textual, TXT ou Markdown. Conteúdo externo é recuperado como dado não confiável, com referências."
      />
      <div className="toolbar">
        <label className="file-button">
          {busy ? "Extraindo…" : "+ Importar documento"}
          <input
            type="file"
            disabled={busy}
            accept=".pdf,.txt,.md"
            onChange={async (e) => {
              const f = e.target.files?.[0];
              if (!f) return;
              setBusy(true);
              try {
                const form = new FormData();
                form.append("file", f);
                await api("/knowledge", { method: "POST", body: form });
                await load();
              } catch (e) {
                notify((e as Error).message);
              } finally {
                setBusy(false);
              }
              e.target.value = "";
            }}
          />
        </label>
        <small>Até 10 MB · PDF sem OCR · UTF-8</small>
      </div>
      <form
        className="toolbar"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            setResults(
              await api("/knowledge/search?q=" + encodeURIComponent(q)),
            );
          } catch (e) {
            notify((e as Error).message);
          }
        }}
      >
        <input
          required
          aria-label="Pesquisar trechos"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar trechos e suas fontes…"
        />
        <button>Pesquisar</button>
      </form>
      {results.map((r, i) => (
        <div className="card" key={i}>
          <small>
            {r.name} · trecho {r.position + 1}
          </small>
          <p>{r.content}</p>
        </div>
      ))}
      {docs.map((d) => (
        <article key={d.id} className="card document">
          <div>
            <h3>{d.name}</h3>
            <small>
              {d.characters.toLocaleString("pt-BR")} caracteres ·{" "}
              {new Date(d.created).toLocaleString("pt-BR")}
            </small>
          </div>
          <button
            className="danger"
            onClick={async () => {
              if (
                confirm(
                  "Excluir documento e seus trechos? Backups não serão alterados.",
                )
              )
                try {
                  await api(`/knowledge/${d.id}?confirm=true`, {
                    method: "DELETE",
                  });
                  await load();
                } catch (e) {
                  notify((e as Error).message);
                }
            }}
          >
            Excluir
          </button>
        </article>
      ))}
      {!docs.length && (
        <Empty text="Sua biblioteca está vazia. Importe um documento para habilitar a recuperação de fontes." />
      )}
    </>
  );
}
export function Voices({
  prefs,
  save,
  voices,
  speak,
}: {
  prefs: Prefs;
  save: (p: Prefs) => Promise<void>;
  voices: SpeechSynthesisVoice[];
  speak: (s: string) => void;
}) {
  const [profile, setProfile] = useState("");
  const v = prefs.voice;
  const change = (key: string, value: unknown) =>
    void save({ ...prefs, voice: { ...v, [key]: value } });
  return (
    <>
      <PageTitle
        eyebrow="IDENTIDADE VOCAL"
        title="Uma voz para Saly"
        text="Vozes reais fornecidas pelo seu navegador e sistema. Disponibilidade, gênero e processamento local variam conforme o dispositivo."
      />
      <div className="card">
        <label>
          Voz principal
          <select
            value={v.voiceURI}
            onChange={(e) => change("voiceURI", e.target.value)}
          >
            <option value="">Preferir português brasileiro disponível</option>
            {[...voices]
              .sort(
                (a, b) =>
                  Number(b.lang === "pt-BR") - Number(a.lang === "pt-BR"),
              )
              .map((x) => (
                <option key={x.voiceURI} value={x.voiceURI}>
                  {x.name} · {x.lang} ·{" "}
                  {x.localService ? "sistema local" : "serviço do navegador"}
                </option>
              ))}
          </select>
        </label>
        {!voices.length && (
          <p role="status">Nenhuma voz disponível neste navegador.</p>
        )}
        <p className="muted">
          A API não informa gênero de forma padronizada. Ouça a amostra para
          escolher uma voz feminina adequada.
        </p>
        {[
          ["rate", "Velocidade", 0.5, 2],
          ["pitch", "Tonalidade", 0.5, 2],
          ["volume", "Volume", 0, 1],
        ].map(([key, label, min, max]) => (
          <label key={key}>
            {label}: {Number(v[key as keyof typeof v]).toFixed(1)}
            <input
              aria-label={String(label)}
              type="range"
              min={min}
              max={max}
              step="0.1"
              value={Number(v[key as keyof typeof v])}
              onChange={(e) => change(String(key), Number(e.target.value))}
            />
          </label>
        ))}
        <label className="check">
          <input
            type="checkbox"
            checked={v.autoSpeak}
            onChange={(e) => change("autoSpeak", e.target.checked)}
          />
          Ler respostas automaticamente
        </label>
        <button
          disabled={!voices.length}
          onClick={() =>
            speak("Olá. Sou Saly. Esta é uma amostra da voz selecionada.")
          }
        >
          Ouvir amostra
        </button>
        <p className="muted">
          SpeechSynthesis: animação aproximada por eventos reais de reprodução;
          amplitude da saída não disponível.
        </p>
      </div>
      <div className="card">
        <h2>Perfis de voz</h2>
        <div className="toolbar">
          <input
            aria-label="Nome do perfil"
            value={profile}
            onChange={(e) => setProfile(e.target.value)}
            placeholder="Nome do perfil"
          />
          <button
            disabled={!profile.trim()}
            onClick={() => {
              change("profiles", [
                ...v.profiles,
                {
                  name: profile,
                  ...{
                    voiceURI: v.voiceURI,
                    rate: v.rate,
                    pitch: v.pitch,
                    volume: v.volume,
                  },
                },
              ]);
              setProfile("");
            }}
          >
            Salvar perfil
          </button>
        </div>
        {v.profiles.map((p, i) => (
          <div className="toolbar" key={i}>
            <span>{p.name}</span>
            <button
              className="secondary"
              onClick={() => void save({ ...prefs, voice: { ...v, ...p } })}
            >
              Aplicar
            </button>
            <button
              className="text-button"
              onClick={() =>
                change(
                  "profiles",
                  v.profiles.filter((_, j) => i !== j),
                )
              }
            >
              Remover
            </button>
          </div>
        ))}
        <small>
          Importação de pacotes e síntese local aguardam um adaptador TTS
          licenciado. Nenhuma voz é baixada automaticamente.
        </small>
      </div>
    </>
  );
}
export function SettingsPanel({
  section,
  prefs,
  save,
  health,
  notify,
}: {
  section: string;
  prefs: Prefs;
  save: (p: Prefs) => Promise<void>;
  health: any;
  notify: (s: string) => void;
}) {
  return (
    <>
      <PageTitle
        eyebrow="PREFERÊNCIAS DO SISTEMA"
        title={
          section === "personality"
            ? "Personalidade"
            : section === "privacy"
              ? "Privacidade"
              : section === "system"
                ? "Sistema e desempenho"
                : "Configurações"
        }
        text="Configurações persistidas no backend, vinculadas à sua conta."
      />
      {(!section || section === "personality") && (
        <div className="card">
          <h2>Personalidade</h2>
          {Object.entries(prefs.personality).map(([key, value]) => (
            <label key={key}>
              {(
                {
                  formality: "Formalidade",
                  conciseness: "Concisão",
                  language: "Idioma",
                  proactivity: "Proatividade",
                  uncertainty: "Diante de incertezas",
                } as Record<string, string>
              )[key] || key}
              <input
                maxLength={500}
                value={value}
                onChange={(e) =>
                  void save({
                    ...prefs,
                    personality: {
                      ...prefs.personality,
                      [key]: e.target.value,
                    },
                  })
                }
              />
            </label>
          ))}
          <small>
            Preferências de estilo não alteram os pesos do modelo nem autorizam
            operações.
          </small>
        </div>
      )}
      {(!section || section === "privacy") && (
        <div className="card">
          <h2>Privacidade e permissões</h2>
          {Object.entries(prefs.privacy).map(([k, v]) => (
            <label className="check" key={k}>
              <input
                type="checkbox"
                checked={v}
                onChange={(e) =>
                  void save({
                    ...prefs,
                    privacy: { ...prefs.privacy, [k]: e.target.checked },
                  })
                }
              />
              {k === "wakeWordEnabled"
                ? "Ao ativar explicitamente o microfone, aguardar a palavra Saly antes de transcrever para o campo"
                : k === "remoteConsent"
                  ? "Autorizo envio ao provedor remoto e às integrações externas configuradas (mensagens, contexto e trechos autorizados)"
                  : k === "useMemory"
                    ? "Recuperar memórias autorizadas no chat"
                    : "Recuperar trechos do Centro Smolin"}
            </label>
          ))}
          <p>
            O microfone só é acessado após ativação. Reconhecimento de fala pode
            enviar áudio ao provedor do navegador. Escuta contínua por nome não
            está habilitada.
          </p>
          <p>
            Memórias contestadas, arquivadas ou desativadas não são recuperadas.
            Exclusões não apagam cópias de backups anteriores.
          </p>
          <button
            onClick={async () => {
              try {
                download("saly-backup-privado.json", await post("/backup"));
              } catch (e) {
                notify((e as Error).message);
              }
            }}
          >
            Exportar meus dados
          </button>
        </div>
      )}
      {(!section || section === "system") && (
        <div className="card">
          <h2>Infraestrutura</h2>
          <p>
            Modelo: {health?.model || "consultando"} ·{" "}
            {health?.model_ready ? "Disponível" : "Indisponível"}
          </p>
          <p>{health?.detail}</p>
          <label>
            Nome interno do acervo
            <input
              value={prefs.collectionName || "Smoln"}
              onChange={(e) =>
                void save({ ...prefs, collectionName: e.target.value })
              }
            />
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={prefs.notifications?.enabled ?? false}
              onChange={(e) =>
                void save({
                  ...prefs,
                  notifications: {
                    quietStart: "22:00",
                    quietEnd: "08:00",
                    timezone: "America/Sao_Paulo",
                    minimumImportance: 0.5,
                    ...prefs.notifications,
                    enabled: e.target.checked,
                  },
                })
              }
            />
            Avisos de lembretes enquanto a aplicação estiver aberta
          </label>
          {prefs.notifications && (
            <label>
              Importância mínima dos avisos:{" "}
              {prefs.notifications.minimumImportance}
              <input
                type="range"
                min="0"
                max="1"
                step=".1"
                value={prefs.notifications.minimumImportance}
                onChange={(e) =>
                  void save({
                    ...prefs,
                    notifications: {
                      ...prefs.notifications!,
                      minimumImportance: Number(e.target.value),
                    },
                  })
                }
              />
            </label>
          )}
          {prefs.notifications && (
            <div className="form-grid">
              <label>
                Silêncio a partir de
                <input
                  type="time"
                  value={prefs.notifications.quietStart}
                  onChange={(e) =>
                    void save({
                      ...prefs,
                      notifications: {
                        ...prefs.notifications!,
                        quietStart: e.target.value,
                      },
                    })
                  }
                />
              </label>
              <label>
                Fim do silêncio
                <input
                  type="time"
                  value={prefs.notifications.quietEnd}
                  onChange={(e) =>
                    void save({
                      ...prefs,
                      notifications: {
                        ...prefs.notifications!,
                        quietEnd: e.target.value,
                      },
                    })
                  }
                />
              </label>
            </div>
          )}
          <label>
            Qualidade gráfica
            <select
              value={prefs.graphics}
              onChange={(e) =>
                void save({
                  ...prefs,
                  graphics: e.target.value as Prefs["graphics"],
                })
              }
            >
              <option value="auto">Adaptativa</option>
              <option value="low">Reduzida</option>
              <option value="high">Alta</option>
              <option value="2d">Alternativa 2D</option>
            </select>
          </label>
          <p className="muted">
            Um único modelo generativo remoto. Recuperação textual e vetorial
            quando configurada. Ajustes LoRA/QLoRA e ativação por nome ainda não
            implementados.
          </p>
        </div>
      )}
    </>
  );
}
export function Activity({ notify }: { notify: (s: string) => void }) {
  const [items, setItems] = useState<any[]>([]),
    [tasks, setTasks] = useState<any[]>([]),
    [task, setTask] = useState(""),
    [expr, setExpr] = useState(""),
    [result, setResult] = useState("");
  const load = () =>
    Promise.all([
      api("/activity").then(setItems),
      api("/lists").then(setTasks),
    ]).catch((e) => notify(e.message));
  useEffect(() => {
    void load();
  }, []);
  return (
    <>
      <PageTitle
        eyebrow="OPERAÇÕES AUDITÁVEIS"
        title="Atividades e ferramentas"
        text="Operações explícitas e controladas. O modelo não executa comandos arbitrários."
      />
      <div className="form-grid">
        <div className="card">
          <h2>Cálculo verificado</h2>
          <form
            className="toolbar"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                setResult(
                  String(
                    (await post("/calculate", { expression: expr })).result,
                  ),
                );
                await load();
              } catch (e) {
                notify((e as Error).message);
              }
            }}
          >
            <input
              aria-label="Expressão aritmética"
              placeholder="(12 + 8) / 4"
              value={expr}
              onChange={(e) => setExpr(e.target.value)}
              required
            />
            <button>Calcular</button>
          </form>
          <output>{result}</output>
        </div>
        <div className="card">
          <h2>Lista interna</h2>
          <form
            className="toolbar"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await post("/lists", { content: task });
                setTask("");
                await load();
              } catch (e) {
                notify((e as Error).message);
              }
            }}
          >
            <input
              required
              maxLength={1000}
              aria-label="Nova tarefa"
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="Uma tarefa para acompanhar…"
            />
            <button>Adicionar</button>
          </form>
          {tasks.map((t) => (
            <label className="check" key={t.id}>
              <input
                type="checkbox"
                checked={t.done}
                onChange={async (e) => {
                  try {
                    await put("/lists/" + t.id, {
                      ...t,
                      done: e.target.checked,
                    });
                    await load();
                  } catch (e) {
                    notify((e as Error).message);
                  }
                }}
              />
              {t.content}
            </label>
          ))}
        </div>
      </div>
      <div className="card">
        <h2>Registro de atividades</h2>
        <button
          className="secondary"
          onClick={() =>
            download("saly-relatorio-atividades.json", {
              created: new Date().toISOString(),
              activities: items,
            })
          }
        >
          Exportar relatório JSON
        </button>
        {items.map((a) => (
          <div className="activity-row" key={a.id}>
            <span className="badge">{a.kind}</span>
            <span>{a.detail}</span>
            <time>{new Date(a.created).toLocaleString("pt-BR")}</time>
          </div>
        ))}
        {!items.length && <Empty text="Nenhuma atividade registrada." />}
      </div>
    </>
  );
}
export function Evaluation({ notify }: { notify: (s: string) => void }) {
  const [runs, setRuns] = useState<any[]>([]),
    [busy, setBusy] = useState(false);
  const load = () =>
    api("/evaluation")
      .then(setRuns)
      .catch((e) => notify(e.message));
  useEffect(() => {
    void load();
  }, []);
  return (
    <>
      <PageTitle
        eyebrow="EVIDÊNCIAS, NÃO PROMESSAS"
        title="Avaliação"
        text="Testes determinísticos de aritmética, limites de ferramentas e integridade SQLite. Estes resultados não medem a precisão linguística do modelo."
      />
      <button
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            await post("/evaluation");
            await load();
          } catch (e) {
            notify((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Executando…" : "Executar avaliação"}
      </button>
      {runs.map((run) => {
        const passed = run.results.filter((r: any) => r.passed).length;
        return (
          <div className="card" key={run.id}>
            <div className="metrics">
              <strong>
                {passed}/{run.results.length}
              </strong>
              <span>
                {Math.round((passed / run.results.length) * 100)}% aprovados
                nesta execução
              </span>
            </div>
            <small>
              {new Date(run.created).toLocaleString("pt-BR")} · Modelo
              configurado: {run.model} (não avaliado)
            </small>
            {run.results.map((r: any, i: number) => (
              <div className="activity-row" key={i}>
                <span>{r.passed ? "✓ Aprovado" : "× Falhou"}</span>
                <span>
                  {r.category} · {r.case}
                </span>
              </div>
            ))}
          </div>
        );
      })}
      {!runs.length && (
        <Empty text="Nenhuma avaliação executada. Nenhuma métrica de desempenho presumida." />
      )}
    </>
  );
}
