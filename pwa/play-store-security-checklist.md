# TailoraHub Play Store Security Checklist

Use this checklist before building the Android Trusted Web Activity package and before every production release.

## Current Automated Checks

- Frontend production build: passing.
- Frontend dependency audit: no known moderate-or-higher vulnerabilities.
- Backend dependency audit: no known vulnerabilities from `pip-audit`.
- Backend tests: passing.
- Repository secret scan: no private keys, AWS access keys, SMTP passwords, database URLs, GitHub tokens or payment live keys found in source files.

## Required Production Configuration

- Keep all backend secrets only on the EC2/server environment, never inside the frontend or Android wrapper.
- Set `JWT_SECRET` and `JWT_REFRESH_SECRET` to stable, different, 32+ byte random values.
- Set `DATABASE_URL` only on the backend server.
- Set SMTP/payment/WhatsApp/admin UPI values only on the backend server.
- Keep `frontend/.env.production` limited to public browser values only, such as `VITE_API_BASE_URL` and restricted Google Maps browser keys.
- Restrict the Google Maps browser key by website referrers and API restrictions.
- Keep `CORS_ORIGINS` limited to:
  - `https://tailorahub.com`
  - `https://www.tailorahub.com`
  - local origins only in development.

## PWA Safety

- Service worker must not cache `/api/` requests.
- Service worker must not cache auth, payment, OTP, user profile, Google Maps or uploaded media responses.
- `manifest.webmanifest`, `sw.js`, icons and `offline.html` must load over HTTPS.
- Offline page should show only generic information, not user/order data.

## Play Store / Android Wrapper Safety

- Do not copy `.env`, `.pem`, `.key`, `.p8`, database credentials or admin credential files into the Android wrapper folder.
- Publish `/.well-known/assetlinks.json` only after adding the release certificate SHA-256 fingerprint from Bubblewrap/Play Console.
- Test the `.aab` using Internal testing before production.
- Fill Play Console Data Safety truthfully for account data, phone/email, location, photos/videos, payment metadata, order/support/dispute data and notifications.

## Manual Final Checks

- Customer, tailor and admin login work after closing and reopening the installed app.
- Map picker loads on Android and respects current-location permissions.
- WhatsApp payment opens correctly and payment requests expire after 5 minutes.
- Admin verification is required before wallet credits/payment status changes.
- Delivery OTP cannot be generated until payment is paid.
- Completed orders hide update/OTP actions and only then show feedback/rating to customer.
