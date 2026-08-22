const SW_URL = "/sw.js";

export function registerPwa() {
  if (!import.meta.env.PROD) return;
  if (!("serviceWorker" in navigator)) return;
  if (!window.isSecureContext) return;

  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register(SW_URL)
      .then((registration) => {
        registration.addEventListener("updatefound", () => {
          const worker = registration.installing;
          if (!worker) return;
          worker.addEventListener("statechange", () => {
            if (worker.state === "installed" && navigator.serviceWorker.controller) {
              window.dispatchEvent(new Event("tailorahub:pwa-update-ready"));
            }
          });
        });
      })
      .catch((error) => {
        console.info("TailoraHub PWA registration skipped.", error);
      });
  });
}
