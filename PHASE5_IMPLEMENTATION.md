# Phase 5 implementation status

## Completed in code

- Added Redis-backed public response caching for the public reference, approved-tailor summary, and active-service endpoints.
- Used an explicit cache allowlist; authenticated requests and customer, tailor, and admin responses are never stored under shared cache keys.
- Added short cache TTLs, `HIT`/`MISS` headers, and generation-based invalidation after relevant successful writes.
- Added distributed per-IP and per-authenticated-session rate limits with stricter OTP, authentication, payment, and upload buckets.
- Added clear JSON `429 Too Many Requests` responses, `Retry-After`, and remaining-limit headers.
- Added bounded normal and upload request bodies with an early `413` response for declared and streamed bodies.
- Added trusted-proxy CIDR handling so forwarded client addresses are accepted only from known load balancers/proxies.
- Added a regional AWS WAF CloudFormation template with AWS managed common, bad-input, reputation, and per-IP rate rules.
- Added a production startup guard requiring the shared Redis traffic store.

## Production variables

```dotenv
TRAFFIC_STORE_BACKEND=redis
REDIS_URL=rediss://your-shared-valkey-endpoint:6379/0
PUBLIC_CACHE_TTL_SECONDS=60
RATE_LIMIT_ENABLED=true
RATE_LIMIT_GENERAL_PER_MINUTE=300
RATE_LIMIT_AUTH_PER_MINUTE=10
RATE_LIMIT_OTP_PER_MINUTE=5
RATE_LIMIT_PAYMENT_PER_MINUTE=10
RATE_LIMIT_UPLOAD_PER_MINUTE=20
MAX_REQUEST_BODY_BYTES=2097152
MAX_UPLOAD_REQUEST_BYTES=26214400
CLIENT_IP_TRUSTED_PROXY_NETWORKS=your-alb-or-vpc-cidr
```

Do not place a public client CIDR in `CLIENT_IP_TRUSTED_PROXY_NETWORKS`; it identifies proxies permitted to supply `X-Forwarded-For`, not users allowed to access the application.

## Cache boundaries

Only these anonymous public response families are cached:

- `/api/reference`
- `/api/tailors`
- `/api/tailors/{tailor_id}/services`
- `/api/v1/tailors/{tailor_id}/services`

Requests containing an authorization header or cookie bypass shared caching. Private API responses are marked `Cache-Control: private, no-store`.

## Remaining AWS validation

The WAF deployment, real proxy CIDRs, multi-replica cache test, limit tuning, and measured production validation are tracked in `PHASE1_PHASE2_PENDING.md`.
