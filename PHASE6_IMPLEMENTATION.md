# Phase 6 implementation status

## Completed in code

- Added configurable connection and response timeouts for external providers.
- Added exponential backoff with jitter for operations explicitly marked safe to retry.
- Prevented automatic retries for payment creation, payment capture, email, and SMS writes where an ambiguous response could duplicate a live side effect.
- Added per-provider circuit breakers with configurable failure and recovery thresholds.
- Replaced raw provider exception messages with secret-safe error categories and structured provider/operation logs.
- Removed the MSG91 API key from its query string; it is sent only through the provider header.
- Added booking and payment idempotency through client keys, PostgreSQL advisory locks, and unique indexes.
- Added a signed Razorpay webhook endpoint with a durable deduplication ledger and idempotent wallet/payment updates.
- Added duplicate-payload protection and support for safe replay after failed or stale webhook processing.
- Disabled legacy unauthenticated/generic payment creation and legacy booking/payment mutations in production.
- Disabled direct live QR wallet credit because it did not prove a captured provider payment; live customers use verified Razorpay booking checkout.
- Added a production startup guard requiring a Razorpay webhook secret whenever Razorpay is active.

## Production variables

```dotenv
RAZORPAY_WEBHOOK_SECRET=inject-from-aws-secrets-manager
EXTERNAL_CONNECT_TIMEOUT_SECONDS=5
EXTERNAL_RESPONSE_TIMEOUT_SECONDS=15
EXTERNAL_SAFE_RETRY_ATTEMPTS=3
EXTERNAL_RETRY_BASE_MS=250
EXTERNAL_CIRCUIT_FAILURE_THRESHOLD=5
EXTERNAL_CIRCUIT_RESET_SECONDS=30
RATE_LIMIT_WEBHOOK_PER_MINUTE=1000
```

Never put the real webhook secret or provider keys in this file, source control, frontend variables, screenshots, or Docker build arguments.

## Razorpay webhook

Configure this production callback:

```text
https://api.tailorahub.com/api/v1/payments/webhooks/razorpay
```

The endpoint verifies `X-Razorpay-Signature` against the exact raw request body before parsing or applying an event. It stores only event identifiers, hashes, provider references, status, and safe error categories--not the full webhook body.

## Idempotency contract

- Production booking creation requires a client key through `idempotencyKey` or `Idempotency-Key`.
- Production Razorpay checkout creation requires the same contract.
- Reusing a key for the same operation returns the existing booking or checkout.
- Reusing a payment key for another booking is rejected.
- The frontend keeps a payment key through ambiguous network failures and clears it after successful verification.

## Remaining production validation

Provider activation, real webhook delivery/replay tests, KYC/payout provider selection, failure drills, and log review are tracked in `PHASE1_PHASE2_PENDING.md`.
