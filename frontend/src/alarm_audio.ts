let audio: AudioContext | null = null;
const oscillators = new Set<OscillatorNode>();
export async function enableAlarmAudio() {
  audio ??= new AudioContext();
  await audio.resume();
  return audio.state === "running";
}
export function alarmAudioReady() {
  return audio?.state === "running";
}
export function stopAlarmAudio() {
  for (const oscillator of oscillators) {
    try {
      oscillator.stop();
    } catch {}
  }
  oscillators.clear();
}
export function playAlarmTone(sound: string) {
  if (!audio || audio.state !== "running") return false;
  stopAlarmAudio();
  for (let index = 0; index < 3; index++) {
    const source = audio.createOscillator(),
      gain = audio.createGain(),
      start = audio.currentTime + index * 0.5;
    source.type = "sine";
    source.frequency.value =
      sound === "bell" ? 880 : sound === "pulse" ? 660 : 440;
    gain.gain.setValueAtTime(0, start);
    gain.gain.linearRampToValueAtTime(0.12, start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, start + 0.35);
    source.connect(gain);
    gain.connect(audio.destination);
    oscillators.add(source);
    source.onended = () => {
      oscillators.delete(source);
      source.disconnect();
      gain.disconnect();
    };
    source.start(start);
    source.stop(start + 0.4);
  }
  return true;
}
