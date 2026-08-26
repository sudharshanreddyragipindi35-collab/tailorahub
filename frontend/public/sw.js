const CACHE_NAME = "tailorahub-pwa-v5";
const APP_SHELL = [
  "/",
  "/offline.html",
  "/manifest.json",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/maskable-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => Promise.allSettled(APP_SHELL.map((path) => cache.add(path))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  const isHttp = url.protocol === "http:" || url.protocol === "https:";
  const isApiRequest = url.pathname.startsWith("/api/") || url.hostname.startsWith("api.");
  const isExternalMapAsset = url.origin.includes("googleapis.com") || url.origin.includes("gstatic.com");
  if (!isHttp || isApiRequest || isExternalMapAsset) {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put("/", copy));
          return response;
        })
        .catch(async () => (
          (await caches.match("/"))
          || (await caches.match("/offline.html"))
          || new Response("You are offline.", { status: 503, headers: { "Content-Type": "text/plain" } })
        ))
    );
    return;
  }

  if (url.origin !== self.location.origin) return;

  event.respondWith(
    fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return response;
        })
      .catch(async () => (
        (await caches.match(request))
        || new Response("Resource unavailable.", { status: 503, headers: { "Content-Type": "text/plain" } })
      ))
  );
});
