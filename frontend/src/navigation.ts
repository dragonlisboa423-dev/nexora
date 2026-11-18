export type Area =
  "conversation" | "knowledge" | "media" | "routine" | "advanced";
export function areaFor(path: string): Area {
  if (path === "/") return "conversation";
  if (
    path.startsWith("/knowledge") ||
    ["/memory", "/library", "/space"].some(
      (p) => path === p || path.startsWith(p + "/"),
    )
  )
    return "knowledge";
  if (path === "/studio" || path === "/media") return "media";
  if (["/routine", "/agenda", "/alarms", "/purchases"].includes(path))
    return "routine";
  return "advanced";
}
export const areaLabels = {
  conversation: "Conversa",
  knowledge: "Conhecimento",
  media: "Mídia",
  routine: "Rotina",
  advanced: "Ajustes",
};
export const areaLinks: Record<string, { to: string; name: string }[]> = {
  knowledge: [
    { to: "/knowledge", name: "Centro Memorial" },
    { to: "/memory", name: "Memórias" },
    { to: "/knowledge/documents", name: "Centro Smolin" },
    { to: "/library", name: "Biblioteca" },
    { to: "/space", name: "Espaço" },
  ],
  routine: [
    { to: "/routine", name: "Minha rotina" },
    { to: "/agenda", name: "Agenda" },
    { to: "/alarms", name: "Alarmes" },
    { to: "/purchases", name: "Compras" },
  ],
  advanced: [
    { to: "/advanced", name: "Visão geral" },
    { to: "/settings", name: "Preferências" },
    { to: "/voices", name: "Vozes" },
    { to: "/advanced/media", name: "Provedores de mídia" },
  ],
};
