# Phase 2 implementation status

## Completed in code

- Removed the recurring 5-second and 15-second dashboard refresh loops.
- Added visibility-, focus-, online-, and mutation-driven refreshes for dashboard collections.
- Added a WebSocket-first booking update hook with heartbeat, reconnect, and a 60-second fallback refresh only while the socket is unavailable.
- Connected live booking updates to customer order details and tailor measurement visits.
- Added backend heartbeat replies for booking tracking sockets.
- Deferred status and payment-breakdown requests until a customer expands an order card.
- Lazy-loaded the map picker with a small loading fallback.
- Split the production bundle into application, React, icon, and map chunks.
- Added lazy image loading and asynchronous decoding for non-critical portfolio, offer, QR, and card media.
- Converted the 1.48 MB landing PNG into a 1600 x 900 WebP of approximately 37 KB.
- Added a repeatable `npm run optimize:images` command.
- Updated the service worker to cache Vite's content-hashed immutable assets cache-first while retaining network-first navigation and API behavior.
- Kept large lists bounded through the Phase 1 pagination limits, so virtualization is not currently required.

## Verification

- Frontend production build: passed.
- Backend regression suite: 20 tests passed, including the WebSocket heartbeat test.
- Production output: main application chunk approximately 272 KB, React chunk approximately 194 KB, icon chunk approximately 16 KB, and lazy map chunk approximately 9 KB before gzip.
- Landing asset emitted as WebP at approximately 37 KB.

## Remaining measured validation

Deferred device and network validation is maintained in `PHASE1_PHASE2_PENDING.md`.
