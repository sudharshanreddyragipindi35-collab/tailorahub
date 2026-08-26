const SW_URL = "/sw.js";

export function registerPwa() {
  if (!import.meta.env.PROD) return;
  if (!("serviceWorker" in navigator)) return;
  if (!window.isSecureContext) return;

  if (window.__TAILORAHUB_SINGLE_FILE__) {
    navigator.serviceWorker.getRegistrations().then((registrations) => Promise.all(registrations.map((registration) => registration.unregister())));
    if ("caches" in window) caches.keys().then((keys) => Promise.all(keys.map((key) => caches.delete(key))));
    return;
  }

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
