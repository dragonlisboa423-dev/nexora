import type { SalyState } from "./api";
export const stateLabels: Record<SalyState, string> = {
  synthesizing: "Preparando áudio",
  idle: "Em repouso",
  listening: "Escutando",
  thinking: "Gerando resposta",
  responding: "Respondendo",
  speaking: "Falando",
  paused: "Fala pausada",
  executing: "Executando operação",
  error: "Atenção necessária",
  transcribing: "Transcrevendo voz",
  searching: "Consultando fontes",
  reading_document: "Processando documento",
  executing_tool: "Executando ferramenta",
  success: "Operação confirmada",
  offline: "Sem conexão",
};
