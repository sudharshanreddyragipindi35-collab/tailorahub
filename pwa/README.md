# TailoraHub PWA

This folder keeps the Play Store and PWA packaging work separate from the existing FastAPI backend and React frontend.

## What Was Added

- `frontend/public/manifest.json` and `frontend/public/manifest.webmanifest` for install metadata, icons, theme color, shortcuts and standalone display.
- `frontend/public/sw.js` for a safe app shell/offline page cache. It does not cache API, auth, payment, Google Maps or dynamic user data.
- `frontend/public/offline.html` for a branded offline fallback.
- `frontend/src/registerPwa.js` to register the service worker only in production builds.
- `pwa/scripts/generate-icons.ps1` to regenerate required PWA icons.
- `pwa/play-store-deployment.md` for the full Android Play Store path.
- `pwa/twa/assetlinks-template.json` for Trusted Web Activity verification.

## Local PWA Test

Run the frontend as a production preview, not Vite dev mode, because the service worker is intentionally enabled only for production builds.

```powershell
cd "C:\Users\sudha\Downloads\TailorLink Full Stack Application\frontend"
npm run build
npm run preview
```

Open:

```text
http://127.0.0.1:5173
```

Chrome DevTools checks:

- Application > Manifest: TailoraHub manifest should load.
- Application > Service Workers: `/sw.js` should be activated.
- Lighthouse > Progressive Web App: run a PWA audit.
- Browser address bar: install icon should appear after manifest + service worker are valid.

## Production PWA Test

After deploying the latest frontend:

```text
https://tailorahub.com/manifest.json
https://tailorahub.com/manifest.webmanifest
https://tailorahub.com/sw.js
https://tailorahub.com/offline.html
```

All three URLs must load over HTTPS.

## Backend Rule

The PWA is only the frontend install experience. The FastAPI backend stays separate and must remain HTTPS:

```text
https://api.tailorahub.com/api/health
```
