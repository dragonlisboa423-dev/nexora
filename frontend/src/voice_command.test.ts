import { describe, it, expect } from "vitest";
import { voiceCommand } from "./voice_command";
describe("foreground voice activation", () => {
  it("requires wake name outside the bounded conversation window", () => {
    expect(voiceCommand("leia genética", 100, 0)).toBeNull();
    expect(voiceCommand("SALY, explique genética", 100, 0)?.command).toBe(
      "explique genética",
    );
    expect(voiceCommand("sali", 100, 0)).toEqual({
      command: "",
      activated: true,
    });
  });
  it("accepts consecutive commands only before expiry", () => {
    expect(voiceCommand("e a evolução?", 120, 150)?.command).toBe(
      "e a evolução?",
    );
    expect(voiceCommand("e a evolução?", 150, 150)).toBeNull();
  });
});
