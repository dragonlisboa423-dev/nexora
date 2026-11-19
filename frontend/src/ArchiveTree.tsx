import { useState } from "react";
import { api } from "./api";
type Entry = {
  index: number;
  path: string;
  size: number;
  directory: boolean;
  status: string;
  pages: number;
  notice?: string;
};
function Branch({
  entries,
  prefix = "",
  id,
}: {
  entries: Entry[];
  prefix?: string;
  id: string;
}) {
  const files = entries.filter((e) => e.path.startsWith(prefix));
  const names = [
    ...new Set(
      files
        .map((e) => e.path.slice(prefix.length).split("/")[0])
        .filter(Boolean),
    ),
  ];
  return (
    <ul>
      {names.map((name) => {
        const path = prefix + name;
        const direct = files.find((e) => e.path === path);
        const children = files.filter((e) => e.path.startsWith(path + "/"));
        return (
          <li key={path}>
            {children.length ? (
              <details>
                <summary>{name}/</summary>
                <Branch entries={children} prefix={path + "/"} id={id} />
              </details>
            ) : direct && !direct.directory ? (
              <>
                <span>
                  {name} · {direct.status} · {direct.size.toLocaleString()}{" "}
                  bytes · {direct.pages} páginas
                </span>{" "}
                {direct.status !== "blocked" && (
                  <>
                    <a
                      href={`/api/knowledge/${id}/entries/${direct.index}/original`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Abrir
                    </a>
                    {" · "}
                    <a
                      href={`/api/knowledge/${id}/entries/${direct.index}/original?download=true`}
                      download
                    >
                      Baixar
                    </a>
                  </>
                )}
                {direct.notice && <small> — {direct.notice}</small>}
              </>
            ) : (
              <span>{name}/ (vazia)</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
export function ArchiveTree({
  id,
  notify,
}: {
  id: string;
  notify: (s: string) => void;
}) {
  const [entries, setEntries] = useState<Entry[] | null>(null);
  return (
    <details
      className="archive-tree"
      onToggle={(e) => {
        if (e.currentTarget.open && !entries)
          api("/knowledge/" + id)
            .then((d) => setEntries(d.archive_entries || []))
            .catch((e) => notify(e.message));
      }}
    >
      <summary>Arquivos e pastas do ZIP</summary>
      {entries ? (
        entries.length ? (
          <Branch entries={entries} id={id} />
        ) : (
          <p>
            Índice interno ainda não disponível. Confira o estado do
            processamento.
          </p>
        )
      ) : (
        <p>Carregando…</p>
      )}
    </details>
  );
}
