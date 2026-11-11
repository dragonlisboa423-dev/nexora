import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  emit,
  operationalState,
  resetOperations,
  transition,
} from "./operations";
describe("real operation state", () => {
  beforeEach(() => {
    resetOperations();
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });
  it("tracks microphone start and explicit stop", () => {
    emit({ type: "MIC_STARTED", id: "microphone" });
    expect(operationalState()).toBe("listening");
    emit({ type: "MIC_STOPPED", id: "microphone" });
    expect(operationalState()).toBe("idle");
  });
  it("never clears a concurrent microphone when a document completes", () => {
    emit({ type: "DOCUMENT_PROCESSING_STARTED", id: "pdf" });
    emit({ type: "MIC_STARTED", id: "mic" });
    emit({ type: "DOCUMENT_INDEXED", id: "pdf" });
    vi.runAllTimers();
    expect(operationalState()).toBe("listening");
  });
  it("uses token and playback events rather than timers for processing", () => {
    emit({ type: "MODEL_REQUEST_STARTED", id: "chat" });
    vi.advanceTimersByTime(300000);
    expect(operationalState()).toBe("thinking");
    emit({ type: "MODEL_TOKEN_RECEIVED", id: "chat" });
    expect(operationalState()).toBe("responding");
    emit({ type: "MODEL_RESPONSE_COMPLETED", id: "chat" });
    expect(operationalState()).toBe("success");
    emit({ type: "SPEECH_STARTED", id: "chat" });
    vi.runAllTimers();
    expect(operationalState()).toBe("speaking");
    emit({ type: "SPEECH_CANCELLED", id: "chat" });
    expect(operationalState()).toBe("idle");
  });
  it("fades only a confirmed acknowledgement and does not erase a new operation", () => {
    emit({ type: "TOOL_STARTED", id: "tool" });
    emit({ type: "TOOL_COMPLETED", id: "tool" });
    expect(operationalState()).toBe("success");
    emit({ type: "TOOL_STARTED", id: "tool" });
    vi.advanceTimersByTime(1000);
    expect(operationalState()).toBe("executing_tool");
    emit({ type: "TOOL_COMPLETED", id: "tool" });
    vi.runAllTimers();
    expect(operationalState()).toBe("idle");
  });
  it("represents offline, recovery, transcription and pause explicitly", () => {
    transition("voice", "transcribing");
    expect(operationalState()).toBe("transcribing");
    emit({ type: "CONNECTION_LOST", id: "network" });
    expect(operationalState()).toBe("offline");
    emit({ type: "CONNECTION_RESTORED", id: "network" });
    expect(operationalState()).toBe("transcribing");
    transition("voice", "paused");
    expect(operationalState()).toBe("paused");
  });
  it("does not report success when a tool failed or awaits approval", () => {
    emit({ type: "TOOL_STARTED", id: "tool" });
    emit({ type: "TOOL_APPROVAL_REQUIRED", id: "tool" });
    expect(operationalState()).toBe("idle");
    emit({ type: "TOOL_FAILED", id: "tool" });
    expect(operationalState()).toBe("error");
  });
});
