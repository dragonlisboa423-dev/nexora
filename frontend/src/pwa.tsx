import { useEffect, useState } from "react";
export function PwaUpdate() {
  const [waiting, setWaiting] = useState<ServiceWorker | null>(null),
    [install, setInstall] = useState<any>(null);
  useEffect(() => {
    if (!("serviceWorker" in navigator) || import.meta.env.DEV) return;
    let disposed = false;
    navigator.serviceWorker
      .register("/sw.js")
      .then((reg) => {
        if (disposed) return;
        if (reg.waiting) setWaiting(reg.waiting);
        reg.addEventListener("updatefound", () => {
          const worker = reg.installing;
          worker?.addEventListener("statechange", () => {
            if (
              worker.state === "installed" &&
              navigator.serviceWorker.controller
            )
              setWaiting(worker);
          });
        });
      })
      .catch(() => {});
    const listener = (e: Event) => {
      e.preventDefault();
      setInstall(e);
    };
    window.addEventListener("beforeinstallprompt", listener);
    return () => {
      disposed = true;
      window.removeEventListener("beforeinstallprompt", listener);
    };
  }, []);
  return (
    <>
      {waiting && (
        <div className="notice" role="status">
          Uma nova versão está disponível.
          <button
            onClick={() => {
              navigator.serviceWorker.addEventListener(
                "controllerchange",
                () => location.reload(),
                { once: true },
              );
              waiting.postMessage({ type: "SKIP_WAITING" });
            }}
          >
            Atualizar agora
          </button>
        </div>
      )}
      {install && (
        <button
          className="install-app secondary"
          onClick={async () => {
            await install.prompt();
            setInstall(null);
          }}
        >
          Instalar SALY neste dispositivo
        </button>
      )}
    </>
  );
}
