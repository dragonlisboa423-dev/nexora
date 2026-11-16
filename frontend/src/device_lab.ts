type Result = {
  id: string;
  category: string;
  status: "passed" | "failed" | "inconclusive";
  duration_ms: number;
  detail: string;
  observed: Record<string, unknown>;
};
export async function deviceChecks(): Promise<Result[]> {
  const results: Result[] = [];
  async function run(
    id: string,
    category: string,
    check: () => Promise<Pick<Result, "status" | "detail" | "observed">>,
  ) {
    const start = performance.now();
    try {
      results.push({
        id,
        category,
        ...(await check()),
        duration_ms: Math.round((performance.now() - start) * 1000) / 1000,
      });
    } catch {
      results.push({
        id,
        category,
        status: "failed",
        detail:
          "Probe não concluído; confira suporte, permissões e armazenamento.",
        observed: {},
        duration_ms: Math.round((performance.now() - start) * 1000) / 1000,
      });
    }
  }
  await run("audio", "Áudio deste navegador", async () => {
    if (!window.AudioContext)
      return {
        status: "inconclusive",
        detail: "AudioContext indisponível.",
        observed: {},
      };
    const context = new AudioContext();
    try {
      await context.resume();
      if (context.state !== "running")
        return {
          status: "inconclusive",
          detail:
            "Áudio bloqueado; use um gesto explícito e revise permissões.",
          observed: { state: context.state },
        };
      const oscillator = context.createOscillator(),
        gain = context.createGain(),
        analyser = context.createAnalyser();
      gain.gain.value = 0.025;
      oscillator.frequency.value = 440;
      oscillator.connect(gain).connect(analyser).connect(context.destination);
      oscillator.start();
      const samples = new Float32Array(analyser.fftSize);
      await new Promise((r) => setTimeout(r, 120));
      analyser.getFloatTimeDomainData(samples);
      const peak = Math.max(...samples.map(Math.abs));
      oscillator.stop();
      return {
        status: peak > 0 ? "passed" : "inconclusive",
        detail:
          "Oscilador/PCM/AudioContext executados com som curto. Não comprova alto-falante físico nem voz neural.",
        observed: { sampleRate: context.sampleRate, pcmPeak: peak },
      };
    } finally {
      await context.close();
    }
  });
  await run("indexeddb", "IndexedDB deste navegador", async () => {
    const name = "saly-lab-" + crypto.randomUUID();
    let db: IDBDatabase | undefined;
    try {
      db = await new Promise<IDBDatabase>((resolve, reject) => {
        const request = indexedDB.open(name, 1);
        request.onupgradeneeded = () =>
          request.result.createObjectStore("probe");
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
      await new Promise<void>((resolve, reject) => {
        const transaction = db!.transaction("probe", "readwrite");
        transaction.objectStore("probe").put("probe-ok", "key");
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(transaction.error);
      });
      const value = await new Promise((resolve, reject) => {
        const request = db!
          .transaction("probe", "readonly")
          .objectStore("probe")
          .get("key");
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
      if (value !== "probe-ok") throw new Error("Divergência");
      return {
        status: "passed",
        detail:
          "Escrita/leitura reais em banco técnico descartável, sem abrir o cofre privado. Não certifica armazenamento permanente no aparelho.",
        observed: {
          writeRead: true,
          persistentStorage: (await navigator.storage?.persisted?.()) ?? false,
        },
      };
    } finally {
      db?.close();
      indexedDB.deleteDatabase(name);
    }
  });
  await run("cache", "Cache público deste navegador", async () => {
    if (!("caches" in window))
      return {
        status: "inconclusive",
        detail: "Cache Storage não disponível.",
        observed: {},
      };
    const names = (await caches.keys()).filter((n) => n.startsWith("saly-"));
    let entries = 0;
    for (const name of names) {
      const cache = await caches.open(name);
      for (const request of await cache.keys()) {
        entries++;
        if (new URL(request.url).pathname.startsWith("/api/"))
          return {
            status: "failed",
            detail:
              "Entrada API indevida no cache público. Remova o cache antigo e revise o service worker.",
            observed: { apiEntryFound: true },
          };
      }
    }
    return {
      status: names.length ? "passed" : "inconclusive",
      detail:
        "Inspecionou caches SALY existentes; nenhum dado da API deve ser armazenado neles. Teste em modo avião continua necessário.",
      observed: {
        caches: names.length,
        entries,
        serviceWorkerControlled: Boolean(navigator.serviceWorker?.controller),
      },
    };
  });
  return results;
}
