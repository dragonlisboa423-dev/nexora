import { useSyncExternalStore } from "react";
import type { SalyState } from "./api";
export type EventType =
  | "MIC_STARTED"
  | "MIC_STOPPED"
  | "TRANSCRIPTION_STARTED"
  | "TRANSCRIPTION_COMPLETED"
  | "MESSAGE_SUBMITTED"
  | "MODEL_REQUEST_STARTED"
  | "MODEL_TOKEN_RECEIVED"
  | "MODEL_RESPONSE_COMPLETED"
  | "TOOL_STARTED"
  | "TOOL_APPROVAL_REQUIRED"
  | "TOOL_COMPLETED"
  | "TOOL_FAILED"
  | "DOCUMENT_UPLOAD_STARTED"
  | "DOCUMENT_UPLOAD_COMPLETED"
  | "DOCUMENT_PROCESSING_STARTED"
  | "DOCUMENT_INDEXED"
  | "DOCUMENT_PROCESSING_FAILED"
  | "SPEECH_STARTED"
  | "SPEECH_ENDED"
  | "SPEECH_CANCELLED"
  | "CONNECTION_LOST"
  | "CONNECTION_RESTORED";
export type OperationEvent = { type: EventType; id: string };
const starts: Partial<Record<EventType, SalyState>> = {
  MIC_STARTED: "listening",
  TRANSCRIPTION_STARTED: "transcribing",
  MESSAGE_SUBMITTED: "thinking",
  MODEL_REQUEST_STARTED: "thinking",
  MODEL_TOKEN_RECEIVED: "responding",
  TOOL_STARTED: "executing_tool",
  DOCUMENT_UPLOAD_STARTED: "reading_document",
  DOCUMENT_PROCESSING_STARTED: "reading_document",
  SPEECH_STARTED: "speaking",
  CONNECTION_LOST: "offline",
};
const priority: SalyState[] = [
  "offline",
  "listening",
  "speaking",
  "paused",
  "executing_tool",
  "searching",
  "responding",
  "thinking",
  "transcribing",
  "reading_document",
  "success",
  "error",
  "idle",
];
let active: Record<string, SalyState> = {};
const revision: Record<string, number> = {};
const listeners = new Set<() => void>();
export function operationalState() {
  return priority.find((s) => Object.values(active).includes(s)) || "idle";
}
export function transition(id: string, state: SalyState) {
  revision[id] = (revision[id] || 0) + 1;
  if (state === "idle") delete active[id];
  else active[id] = state;
  listeners.forEach((fn) => fn());
}
export function emit(event: OperationEvent) {
  const start = starts[event.type];
  if (
    ["TOOL_COMPLETED", "DOCUMENT_INDEXED", "MODEL_RESPONSE_COMPLETED"].includes(
      event.type,
    ) &&
    active[event.id]
  ) {
    transition(event.id, "success");
    const token = revision[event.id];
    // Only the acknowledgement animation fades by time; task completion has already been confirmed.
    setTimeout(() => {
      if (revision[event.id] === token) transition(event.id, "idle");
    }, 650);
  } else if (
    ["TOOL_FAILED", "DOCUMENT_PROCESSING_FAILED"].includes(event.type)
  ) {
    transition(event.id, "error");
  } else transition(event.id, start || "idle");
}
export function resetOperations() {
  active = {};
  listeners.forEach((fn) => fn());
}
export function useOperations() {
  return useSyncExternalStore((fn) => {
    listeners.add(fn);
    return () => {
      listeners.delete(fn);
    };
  }, operationalState);
}
