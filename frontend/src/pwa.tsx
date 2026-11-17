import { useEffect, useState } from "react";
export function PwaUpdate() {
  const [warning, setWarning] = useState("");
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
      .catch(() =>
        setWarning(
          "Não foi possível preparar o acesso offline. Verifique HTTPS, espaço local e permissões do navegador.",
        ),
      );
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
      {warning && (
        <div className="notice" role="status">
          {warning}
          <button onClick={() => setWarning("")}>Fechar aviso</button>
        </div>
      )}
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
