import { useEffect, useState } from "react";
import { api, post } from "./api";
import { Link } from "react-router-dom";
import { ImagePlus, Film, Images, History, Plus } from "lucide-react";
import { PageTitle } from "./Panels";
type Data = Record<string, any>;
const states: Record<string, string> = {
  queued: "Na fila",
  running: "Executando",
  cancel_requested: "Cancelamento solicitado",
  cancelled: "Cancelada",
  completed: "Concluída com arquivo validado",
  failed: "Falhou",
};
export default function Studio({ notify }: { notify: (s: string) => void }) {
  const [workspace, setWorkspace] = useState<
    "image" | "video" | "gallery" | "history"
  >("image");
  const [caps, setCaps] = useState<Data | null>(null),
    [assets, setAssets] = useState<Data[]>([]),
    [jobs, setJobs] = useState<Data[]>([]),
    [kind, setKind] = useState("image"),
    [busy, setBusy] = useState(false),
    [feedback, setFeedback] = useState(""),
    [scenes, setScenes] = useState<Data[]>([]),
    [orientation, setOrientation] = useState("landscape"),
    [transition, setTransition] = useState("cut"),
    [narration, setNarration] = useState(""),
    [music, setMusic] = useState(""),
    [prompt, setPrompt] = useState(""),
    [steps, setSteps] = useState(4),
    [edit, setEdit] = useState(""),
    [rotate, setRotate] = useState(0),
    [cropEnabled, setCropEnabled] = useState(false),
    [crop, setCrop] = useState([0, 0, 100, 100]);
  async function refresh() {
    const [c, a, j] = await Promise.all([
      api("/media/capabilities"),
      api("/media/assets"),
      api("/media/jobs"),
    ]);
    setCaps(c);
    setAssets(a);
    setJobs(j);
  }
  useEffect(() => {
    let alive = true;
    const read = async () => {
      try {
        const [c, a, j] = await Promise.all([
          api("/media/capabilities"),
          api("/media/assets"),
          api("/media/jobs"),
        ]);
        if (alive) {
          setCaps(c);
          setAssets(a);
          setJobs(j);
        }
      } catch (e) {
        if (alive) notify((e as Error).message);
      }
    };
    void read();
    const timer = setInterval(() => {
      if (!document.hidden) void read();
    }, 5000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);
  const images = assets.filter((a) => a.kind === "image"),
    visual = assets.filter((a) => ["image", "video"].includes(a.kind)),
    audio = assets.filter((a) => a.kind === "audio");
  return (
    <>
      <PageTitle
        eyebrow="MÍDIA · SEU ATELIÊ"
        title="Dê forma às suas ideias."
        text="Imagens, movimento e histórias feitas por você."
      />
      {!caps && <p>Consultando motores disponíveis…</p>}
      <div
        className="studio-navigation"
        role="tablist"
        aria-label="Espaços de criação"
        onKeyDown={(e) => {
          const choices = ["image", "video", "gallery", "history"] as const;
          const focused = (e.target as HTMLElement)
            .closest('[role="tab"]')
            ?.id.replace("studio-tab-", "");
          const at = choices.findIndex((id) => id === focused);
          const current = at < 0 ? choices.indexOf(workspace) : at;
          const next =
            e.key === "ArrowRight"
              ? (current + 1) % 4
              : e.key === "ArrowLeft"
                ? (current + 3) % 4
                : e.key === "Home"
                  ? 0
                  : e.key === "End"
                    ? 3
                    : -1;
          if (next < 0) return;
          e.preventDefault();
          setWorkspace(choices[next]);
          document.getElementById(`studio-tab-${choices[next]}`)?.focus();
        }}
      >
        {(
          [
            ["image", "Imagem", ImagePlus],
            ["video", "Vídeo", Film],
            ["gallery", "Galeria", Images],
            ["history", "Produções", History],
          ] as const
        ).map(([id, label, Icon]) => (
          <button
            role="tab"
            aria-label={label}
            tabIndex={workspace === id ? 0 : -1}
            aria-selected={workspace === id}
            aria-controls={`studio-${id}`}
            id={`studio-tab-${id}`}
            key={id}
            onClick={() => setWorkspace(id)}
          >
            <Icon size={18} strokeWidth={1.3} />
            {label}
            {id === "video" && scenes.length > 0 && (
              <span>{scenes.length}</span>
            )}
          </button>
        ))}
      </div>
      {caps && (
        <section
          className="card studio-generator studio-panel"
          role="tabpanel"
          id="studio-image"
          aria-labelledby="studio-tab-image"
          hidden={workspace !== "image"}
        >
          <div className="studio-section-heading">
            <div>
              <small>DO PENSAMENTO À IMAGEM</small>
              <h2>O que você imagina?</h2>
            </div>
            <span className="availability">
              {caps.image_generation.configured
                ? "Configurada · teste necessário"
                : "IA não conectada"}
            </span>
          </div>
          <p>
            Descreva uma imagem para o provedor configurado ou edite um arquivo
            seu abaixo. A geração por IA permanece desativada quando não há
            conexão válida.
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (
                !confirm(
                  "Enviar este prompt ao modelo Cloudflare configurado exclusivamente em Workers Free, dentro da cota compartilhada?",
                )
              )
                return;
              try {
                await post("/media/images/generate", {
                  prompt,
                  steps,
                  confirm: true,
                });
                await refresh();
                setWorkspace("history");
              } catch (e) {
                notify((e as Error).message);
              }
            }}
          >
            <label>
              Descrição da imagem
              <textarea
                maxLength={2048}
                required
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
              />
            </label>
            <details className="studio-options">
              <summary>Ajustes da imagem</summary>
              <label>
                Passos de difusão
                <input
                  type="number"
                  min="1"
                  max="8"
                  value={steps}
                  onChange={(e) => setSteps(Number(e.target.value))}
                />
              </label>
            </details>
            <button disabled={!caps.image_generation.configured}>
              {caps.image_generation.configured
                ? "Testar geração configurada"
                : "Geração de imagem não conectada"}
            </button>
          </form>{" "}
          <Link className="studio-advanced-link" to="/advanced/media">
            Disponibilidade e opções avançadas ↗
          </Link>
        </section>
      )}
      <div className="studio-video-notice" hidden={workspace !== "video"}>
        <Film size={22} strokeWidth={1.1} />
        <p>
          Combine suas imagens e clipes em um vídeo.{" "}
          <span>Geração de cenas por IA não está conectada.</span>
        </p>
        <Link to="/advanced/media">Ver disponibilidade ↗</Link>
      </div>
      <section
        className="card studio-panel studio-gallery"
        role="tabpanel"
        id="studio-gallery"
        aria-labelledby="studio-tab-gallery"
        hidden={workspace !== "gallery"}
      >
        <h2>A sua galeria</h2>
        <p>
          Use mídias próprias ou licenciadas. Até 10 MB e 60 s por áudio/clipe.
          Imagens: até 8 MB/16 MP, normalizadas em PNG sem metadados. Áudio e
          vídeo são decodificados e reexportados; URLs e playlists não são
          aceitas.
        </p>
        <div className="toolbar">
          <label>
            Tipo do arquivo
            <select
              aria-label="Tipo do arquivo"
              value={kind}
              onChange={(e) => setKind(e.target.value)}
            >
              <option value="image">Imagem</option>
              <option value="video">Clipe de vídeo</option>
              <option value="audio">Áudio/narração</option>
            </select>
          </label>
          <label>
            Enviar mídia privada
            <input
              disabled={busy}
              type="file"
              accept={
                kind === "image"
                  ? "image/png,image/jpeg,image/webp"
                  : kind === "audio"
                    ? "audio/*"
                    : "video/mp4,video/webm"
              }
              onChange={async (e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (!file) return;
                setBusy(true);
                try {
                  const form = new FormData();
                  form.set("file", file);
                  await api("/media/assets?kind=" + kind, {
                    method: "POST",
                    body: form,
                  });
                  await refresh();
                } catch (e) {
                  notify((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            />
          </label>
          <span role="status">
            {busy ? "Validando e normalizando arquivo…" : ""}
          </span>
        </div>
        <div className="asset-gallery">
          {assets.map((asset) => (
            <article className="link-card" key={asset.id}>
              {asset.kind === "image" ? (
                <img
                  loading="lazy"
                  src={`/api/private-assets/${asset.id}`}
                  alt={`Imagem privada ${asset.id.slice(0, 8)}`}
                />
              ) : asset.kind === "video" ? (
                <video
                  controls
                  preload="none"
                  src={`/api/private-assets/${asset.id}`}
                />
              ) : (
                <audio
                  controls
                  preload="none"
                  src={`/api/private-assets/${asset.id}`}
                />
              )}
              <p>
                {asset.kind} · {(asset.size / 1024).toFixed(1)} KB{" "}
                {asset.duration ? `· ${asset.duration.toFixed(2)} s` : ""}
              </p>
              <details className="asset-details">
                <summary>Detalhes do arquivo</summary>
                <code>{asset.id}</code>
                <small>SHA-256: {asset.sha256}</small>
              </details>
              <div className="toolbar">
                {asset.kind === "image" && (
                  <button
                    onClick={() => {
                      setEdit(asset.id);
                      setWorkspace("image");
                    }}
                  >
                    Editar imagem
                  </button>
                )}
                <a
                  download={`saly-${asset.id}.${asset.kind === "video" ? "mp4" : asset.kind === "audio" ? "wav" : "png"}`}
                  href={`/api/private-assets/${asset.id}`}
                >
                  Baixar arquivo
                </a>
                {["image", "video"].includes(asset.kind) && (
                  <button
                    onClick={() =>
                      setScenes([
                        ...scenes,
                        {
                          asset_id: asset.id,
                          duration:
                            asset.kind === "video"
                              ? Math.min(3, asset.duration)
                              : 3,
                          trim_start: 0,
                          caption: "",
                        },
                      ])
                    }
                    disabled={scenes.length >= 8}
                  >
                    Adicionar cena {asset.id.slice(0, 8)}
                  </button>
                )}
                <button
                  onClick={async () => {
                    if (
                      !confirm(
                        "Excluir este arquivo privado? Resultados antigos que o referenciem ficarão sem download.",
                      )
                    )
                      return;
                    try {
                      await api(`/media/assets/${asset.id}?confirm=true`, {
                        method: "DELETE",
                      });
                      await refresh();
                    } catch (e) {
                      notify((e as Error).message);
                    }
                  }}
                >
                  Excluir arquivo {asset.id.slice(0, 8)}
                </button>
              </div>
            </article>
          ))}
        </div>
        {!assets.length && <p>Nenhum arquivo privado no Estúdio.</p>}
      </section>
      <section
        className="card studio-panel studio-edit"
        aria-label="Edição local de imagem"
        hidden={workspace !== "image"}
      >
        <div className="studio-section-heading">
          <div>
            <small>UM NOVO OLHAR</small>
            <h2>Edição local de imagem</h2>
          </div>
          <button className="secondary" onClick={() => setWorkspace("gallery")}>
            <Plus size={15} />
            Adicionar imagem
          </button>
        </div>
        {feedback && <p role="status">{feedback}</p>}
        {edit ? (
          <img
            className="studio-edit-preview"
            src={`/api/private-assets/${edit}`}
            alt="Imagem selecionada para edição"
          />
        ) : (
          <div className="studio-empty-preview">
            <ImagePlus size={42} strokeWidth={0.8} />
            <p>
              Escolha uma imagem da sua galeria.
              <br />O original será preservado.
            </p>
          </div>
        )}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (
              !confirm(
                "Criar nova imagem com este recorte/rotação, preservando a original?",
              )
            )
              return;
            try {
              const result = await post("/media/images/edit", {
                asset_id: edit,
                rotate,
                crop: cropEnabled ? crop : null,
                confirm: true,
              });
              await refresh();
              setEdit(result.id);
              setRotate(0);
              setCropEnabled(false);
              setFeedback(
                "Edição concluída. Esta é a nova imagem; o arquivo original permanece na galeria.",
              );
            } catch (e) {
              notify((e as Error).message);
            }
          }}
        >
          <div className="form-grid">
            <label>
              Imagem a editar
              <select
                aria-label="Imagem a editar"
                required
                value={edit}
                onChange={(e) => setEdit(e.target.value)}
              >
                <option value="">Escolha uma imagem</option>
                {images.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.id.slice(0, 12)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Rotação horária
              <select
                aria-label="Rotação horária"
                value={rotate}
                onChange={(e) => setRotate(Number(e.target.value))}
              >
                {[0, 90, 180, 270].map((v) => (
                  <option key={v} value={v}>
                    {v}°
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label>
            <input
              type="checkbox"
              checked={cropEnabled}
              onChange={(e) => setCropEnabled(e.target.checked)}
            />
            Recortar em coordenadas de pixels
          </label>
          {cropEnabled && (
            <div className="form-grid">
              {["Esquerda x0", "Topo y0", "Direita x1", "Base y1"].map(
                (label, i) => (
                  <label key={label}>
                    {label}
                    <input
                      type="number"
                      min="0"
                      step="1"
                      required
                      value={crop[i]}
                      onChange={(e) =>
                        setCrop(
                          crop.map((v, j) =>
                            i === j ? Number(e.target.value) : v,
                          ),
                        )
                      }
                    />
                  </label>
                ),
              )}
            </div>
          )}
          <button disabled={!edit}>Aplicar edição local</button>
        </form>
      </section>
      <section
        className="card studio-panel studio-montage"
        role="tabpanel"
        id="studio-video"
        aria-labelledby="studio-tab-video"
        hidden={workspace !== "video"}
      >
        <div className="studio-section-heading">
          <div>
            <small>UMA CENA DE CADA VEZ</small>
            <h2>Montagem real de vídeo</h2>
          </div>
          <button className="secondary" onClick={() => setWorkspace("gallery")}>
            <Plus size={15} />
            Escolher arquivos
          </button>
        </div>
        <details className="studio-options">
          <summary>Como esta montagem funciona</summary>
          <p>
            Imagens e clipes são ajustados com margens para preservar proporção.
            Áudio original dos clipes é removido; adicione narração/música
            separadas. Legendas são texto fixo por cena, sem transcrição
            automática. Transição suave usa entrada/saída para preto. Faixas
            curtas são repetidas até o fim.
          </p>
        </details>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (!confirm("Exportar esta montagem local com FFmpeg?")) return;
            try {
              await post("/media/montage", {
                scenes,
                orientation,
                transition,
                narration_asset_id: narration || null,
                music_asset_id: music || null,
                confirm: true,
              });
              await refresh();
              setWorkspace("history");
            } catch (e) {
              notify((e as Error).message);
            }
          }}
        >
          {scenes.map((scene, index) => (
            <fieldset className="scene-card" key={index}>
              <legend>
                Cena {index + 1} · {scene.asset_id.slice(0, 12)}
              </legend>
              {assets.find((a) => a.id === scene.asset_id)?.kind === "image" ? (
                <img
                  className="scene-thumbnail"
                  src={`/api/private-assets/${scene.asset_id}`}
                  alt={`Imagem da cena ${index + 1}`}
                />
              ) : (
                <video
                  className="scene-thumbnail"
                  controls
                  preload="none"
                  src={`/api/private-assets/${scene.asset_id}`}
                />
              )}
              <div className="form-grid">
                {[
                  ["duration", "Duração em segundos"],
                  ["trim_start", "Início do corte em segundos"],
                ].map(([key, label]) => (
                  <label key={key}>
                    {label}
                    <input
                      type="number"
                      min={key === "duration" ? 0.5 : 0}
                      max={key === "duration" ? 15 : 59}
                      step=".1"
                      required
                      value={scene[key]}
                      onChange={(e) =>
                        setScenes(
                          scenes.map((s, i) =>
                            i === index
                              ? { ...s, [key]: Number(e.target.value) }
                              : s,
                          ),
                        )
                      }
                    />
                  </label>
                ))}
                <label>
                  Legenda desta cena
                  <input
                    maxLength={300}
                    disabled={!caps?.montage.captions_available}
                    value={scene.caption}
                    onChange={(e) =>
                      setScenes(
                        scenes.map((s, i) =>
                          i === index ? { ...s, caption: e.target.value } : s,
                        ),
                      )
                    }
                  />
                </label>
              </div>
              <div className="toolbar">
                <button
                  type="button"
                  disabled={index === 0}
                  onClick={() => {
                    const next = [...scenes];
                    [next[index - 1], next[index]] = [
                      next[index],
                      next[index - 1],
                    ];
                    setScenes(next);
                  }}
                >
                  Mover cena antes
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setScenes(scenes.filter((_, i) => i !== index))
                  }
                >
                  Remover cena {index + 1}
                </button>
              </div>
            </fieldset>
          ))}
          <p>
            Total: {scenes.reduce((sum, s) => sum + s.duration, 0).toFixed(1)}{" "}
            s.
          </p>
          <div className="form-grid">
            <label>
              Orientação
              <select
                aria-label="Orientação do vídeo"
                value={orientation}
                onChange={(e) => setOrientation(e.target.value)}
              >
                <option value="landscape">Paisagem 640×360</option>
                <option value="portrait">Retrato 360×640</option>
              </select>
            </label>
            <label>
              Transição
              <select
                aria-label="Transição do vídeo"
                value={transition}
                onChange={(e) => setTransition(e.target.value)}
              >
                <option value="cut">Corte</option>
                <option value="fade">Entrada/saída para preto</option>
              </select>
            </label>
            {[
              ["Narração", narration, setNarration],
              ["Música", music, setMusic],
            ].map(([label, value, set]) => (
              <label key={label as string}>
                {label as string}
                <select
                  aria-label={label as string}
                  value={value as string}
                  onChange={(e) => (set as (s: string) => void)(e.target.value)}
                >
                  <option value="">Sem faixa</option>
                  {audio.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.id.slice(0, 12)} · {a.duration.toFixed(1)} s
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </div>
          <button
            disabled={
              !scenes.length ||
              !caps?.montage.available ||
              scenes.reduce((sum, s) => sum + s.duration, 0) > 60
            }
          >
            Exportar montagem local
          </button>
        </form>
      </section>
      <section
        className="studio-panel"
        role="tabpanel"
        id="studio-history"
        aria-labelledby="studio-tab-history"
        hidden={workspace !== "history"}
      >
        <h2>Suas produções</h2>
        {jobs.map((job) => (
          <article className="card" key={job.id}>
            <h3>
              {job.kind === "montage" ? "Montagem local" : "Geração de imagem"}{" "}
              · {states[job.status]}
            </h3>
            <p>
              {job.provider} · {job.created}
            </p>
            {job.status === "completed" &&
              job.output_asset_ids.map((id: string) => {
                const result = assets.find((a) => a.id === id);
                return result?.kind === "video" ? (
                  <video
                    key={id}
                    className="production-preview"
                    controls
                    preload="none"
                    src={`/api/private-assets/${id}`}
                  />
                ) : result?.kind === "image" ? (
                  <img
                    key={id}
                    loading="lazy"
                    className="production-preview"
                    src={`/api/private-assets/${id}`}
                    alt="Resultado da produção concluída"
                  />
                ) : null;
              })}
            {job.progress && (
              <div>
                <p>
                  {job.progress.stage}:{" "}
                  {job.progress.encoded_seconds.toFixed(2)} /{" "}
                  {job.progress.target_seconds.toFixed(2)} s codificados.
                </p>
                <progress
                  aria-label="Progresso real da etapa"
                  max="100"
                  value={job.progress.percent}
                />
              </div>
            )}
            {job.error && <p role="alert">{job.error}</p>}
            {job.status === "cancel_requested" && (
              <p>
                Interrupção solicitada. Uma requisição remota já enviada pode
                consumir cota; não há cancelamento remoto confirmado.
              </p>
            )}
            <div className="toolbar">
              {["queued", "running", "cancel_requested"].includes(
                job.status,
              ) ? (
                <button
                  disabled={job.status === "cancel_requested"}
                  onClick={() =>
                    post(`/media/jobs/${job.id}/cancel`)
                      .then(refresh)
                      .catch((e) => notify(e.message))
                  }
                >
                  Cancelar tarefa {job.id.slice(0, 8)}
                </button>
              ) : (
                <button
                  onClick={async () => {
                    if (
                      !confirm(
                        "Excluir histórico e arquivos de saída desta tarefa?",
                      )
                    )
                      return;
                    try {
                      await api(`/media/jobs/${job.id}?confirm=true`, {
                        method: "DELETE",
                      });
                      await refresh();
                    } catch (e) {
                      notify((e as Error).message);
                    }
                  }}
                >
                  Excluir tarefa {job.id.slice(0, 8)}
                </button>
              )}
              {job.output_asset_ids.map((id: string) => (
                <a
                  key={id}
                  href={`/api/private-assets/${id}`}
                  download={`saly-${id}.${job.kind === "montage" ? "mp4" : "png"}`}
                >
                  Baixar resultado verificado
                </a>
              ))}
            </div>
            {job.result_sha256 && (
              <details className="asset-details">
                <summary>Verificação do arquivo</summary>
                <small>SHA-256: {job.result_sha256}</small>
              </details>
            )}
          </article>
        ))}
        {!jobs.length && (
          <div className="studio-empty-preview">
            <Film size={40} strokeWidth={1} />
            <p>As suas criações aparecem aqui depois da exportação.</p>
          </div>
        )}
      </section>
      <p>
        Estúdio requer servidor ativo. Arquivos privados não são guardados no
        cache público ou copiados offline automaticamente.
      </p>
    </>
  );
}
