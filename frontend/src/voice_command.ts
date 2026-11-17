/** Wake gating applies only to a user-enabled foreground session. */
export function voiceCommand(
  text: string,
  now: number,
  activeUntil: number,
): { command: string; activated: boolean } | null {
  const wake = /\b(saly|sali)\b/i.exec(text);
  if (wake)
    return {
      command: text
        .slice(wake.index + wake[0].length)
        .replace(/^[.,:!\s]+/, "")
        .trim(),
      activated: true,
    };
  if (now < activeUntil) return { command: text.trim(), activated: false };
  return null;
}
