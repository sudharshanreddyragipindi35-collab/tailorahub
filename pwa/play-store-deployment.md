# TailoraHub PWA to Google Play Store

Use this when the web PWA is tested on `https://tailorahub.com`.

## Step 1: Confirm PWA Requirements

1. Deploy frontend to `https://tailorahub.com`.
2. Confirm these URLs work:
   - `https://tailorahub.com/manifest.json`
   - `https://tailorahub.com/manifest.webmanifest`
   - `https://tailorahub.com/sw.js`
   - `https://tailorahub.com/offline.html`
3. Confirm backend health:
   - `https://api.tailorahub.com/api/health`
4. In Chrome DevTools, run Lighthouse PWA audit.
5. Complete the security checklist:
   - `pwa/play-store-security-checklist.md`

## Step 2: Install Required Tools

Install these on your local machine:

- Node.js LTS
- Java JDK 17
- Android Studio
- Google Play Console account

Then install Bubblewrap:

```powershell
npm install -g @bubblewrap/cli
bubblewrap --version
java -version
```

## Step 3: Create Android TWA Project

Create a separate Android wrapper folder:

```powershell
cd "C:\Users\sudha\Downloads\TailorLink Full Stack Application\pwa"
mkdir android-twa
cd android-twa
bubblewrap init --manifest https://tailorahub.com/manifest.json
```

Use these values when asked:

- Application name: `TailoraHub`
- Short name: `TailoraHub`
- Package ID: `com.tailorahub.app`
- Host: `tailorahub.com`
- Start URL: `/`
- Display mode: `standalone`
- Orientation: `portrait`
- Theme color: `#0b0d10`
- Navigation color: `#050606`

## Step 4: Build App Bundle

```powershell
bubblewrap build
```

Output will be an `.aab` file. Google Play Store uses `.aab`, not APK, for production releases.

## Step 5: Add Digital Asset Links

Bubblewrap will show a SHA-256 certificate fingerprint. Copy it into:

```text
pwa/twa/assetlinks-template.json
```

Then create this production file:

```text
frontend/public/.well-known/assetlinks.json
```

Deploy frontend again and confirm:

```text
https://tailorahub.com/.well-known/assetlinks.json
```

This file proves that the Android app and website belong to the same owner.

## Step 6: Play Console Setup

In Google Play Console:

1. Create app.
2. App name: `TailoraHub`
3. Default language: English.
4. App type: App.
5. Category: Business or Lifestyle.
6. Upload app icon, feature graphic, screenshots and privacy policy URL.
7. Fill Data Safety honestly:
   - Account details
   - Location
   - Photos/videos
   - Payment-related metadata
   - Support/dispute messages
8. Upload `.aab` to Internal testing first.
9. Add testers and test install.
10. Promote to Closed testing, Open testing, then Production.

## Step 7: Before Production Release

Check these carefully:

- Customer, tailor and admin login work.
- Google Maps loads on Android.
- OTP flows work.
- WhatsApp payment redirection opens correctly.
- Order tracking works after reopening the app.
- Offline page appears when internet is disabled.
- No secret keys are in frontend code.
- API calls use only `https://api.tailorahub.com`.

## Recommended Release Flow

Daily work:

```powershell
git checkout daily
```

Stable release:

```powershell
git checkout main
git merge --ff-only daily
git push origin main
```

Then deploy frontend from `main`.
