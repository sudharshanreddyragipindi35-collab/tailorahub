const SW_URL = "/sw.js";

export function registerPwa() {
  if (!import.meta.env.PROD) {
    // A previously installed production service worker can continue to control
    // localhost and serve an old UI even while Vite is running. Development
    // must always use the current source and HMR output.
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .getRegistrations()
        .then((registrations) => Promise.all(registrations.map((registration) => registration.unregister())))
        .catch(() => {});
    }
    if ("caches" in window) {
      caches
        .keys()
        .then((keys) => Promise.all(keys.filter((key) => key.startsWith("tailorahub-")).map((key) => caches.delete(key))))
        .catch(() => {});
    }
    return;
  }
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
