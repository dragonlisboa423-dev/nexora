import { useState } from "react";
export function readCoreMotion() {
  try {
    const v = JSON.parse(localStorage.getItem("saly-core-motion") || "{}");
    return {
      intensity: Math.max(0, Math.min(1, Number(v.intensity ?? 0.65) || 0)),
      speed: Math.max(0.4, Math.min(1.8, Number(v.speed ?? 1) || 1)),
    };
  } catch {
    return { intensity: 0.65, speed: 1 };
  }
}
export function CoreMotion() {
  const [value, setValue] = useState(readCoreMotion);
  return (
    <details className="card">
      <summary>Pulsação do núcleo</summary>
      {(["intensity", "speed"] as const).map((k) => (
        <label key={k}>
          {k === "intensity" ? "Intensidade" : "Velocidade"}
          <input
            aria-label={
              k === "intensity"
                ? "Intensidade da pulsação"
                : "Velocidade da pulsação"
            }
            type="range"
            min={k === "intensity" ? 0 : 0.4}
            max={k === "intensity" ? 1 : 1.8}
            step="0.05"
            value={value[k]}
            onChange={(e) => {
              const next = { ...value, [k]: Number(e.target.value) };
              setValue(next);
              try {
                localStorage.setItem("saly-core-motion", JSON.stringify(next));
              } catch {}
              window.dispatchEvent(new Event("saly-core-motion"));
            }}
          />
        </label>
      ))}
      <small>
        Preferência neste dispositivo. Movimento reduzido pausa os efeitos.
        Bloom somente em qualidade alta e WebGL compatível.
      </small>
    </details>
  );
}
