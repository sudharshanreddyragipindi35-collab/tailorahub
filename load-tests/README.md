# TailoraHub Phase 10 load tests

This directory contains the repeatable Phase 10 k6 test harness. It defaults to one virtual user against `http://127.0.0.1:8001/api`. Remote targets and state-changing suites fail closed until their exact approval environment variables and runner switches are supplied.

## Prerequisites

1. Install [Grafana k6](https://grafana.com/docs/k6/latest/set-up/install-k6/).
2. Start the backend and use dedicated synthetic customer, tailor, and admin accounts.
3. Set tokens and JSON payloads only in the current terminal or a private secret manager. Do not save them in this repository, command transcripts, screenshots, or reports.
4. Keep Phase 8 CloudWatch metrics open while testing.

Run the safe local smoke test:

```powershell
.\deployment\phase10-run-load-test.ps1 -Suite public-read -Profile smoke
```

Profiles are `smoke` (one user for 30 seconds), `baseline` (50), `normal` (100), `growth` (250), `release` (500), `high` (1,000), `spike`, and `soak`. `SOAK_VUS` and `SOAK_DURATION` override the soak defaults of 100 users and four hours.

## Runtime inputs

All values below are environment variables. Required values depend on the selected suite.

| Suite | Required inputs | Coverage |
|---|---|---|
| `public-read` | optional `PUBLIC_TAILOR_ID` | health, public browse, public services |
| `customer-read` | `CUSTOMER_TOKEN`; optional `PUBLIC_TAILOR_ID`, `SEARCH_QUERY` | browse/search response, profile, services/reviews/offers/follow state, favorites, orders, notifications payload |
| `tailor-read` | `TAILOR_TOKEN` | dashboard, orders/notifications/followers, services, waiting list |
| `admin-read` | `ADMIN_TOKEN` | metrics, orders, tailors, support reports; run separately through the approved admin network |
| `auth` | `AUTH_USERS_JSON` | password login and one refresh with each returned refresh token |
| `booking` | `CUSTOMER_TOKEN`, `BOOKING_PAYLOAD`, `BOOKING_IDEMPOTENCY_PREFIX` | preview, submit, repeat identical idempotency key, assert duplicate suppression |
| `tailor-stage` | `TAILOR_TOKEN`, `STAGE_BOOKING_ID`, `STAGE_PAYLOAD` | controlled stage updates |
| `notifications` | customer/tailor token; optional `NOTIFICATION_ROLE` | notification-processing write path |
| `websocket` | `CUSTOMER_TOKEN`, `TRACK_BOOKING_ID`; optional `WS_BASE_URL` | short-lived ticket, upgrade, ping/pong across replicas |
| `media` | `MEDIA_DOWNLOAD_URL`, `MEDIA_UPLOAD_URL`; optional `MEDIA_UPLOAD_BODY`, `MEDIA_CONTENT_TYPE` | CloudFront/S3 download and dedicated presigned synthetic upload |
| `payment` | `CUSTOMER_TOKEN`, `PAYMENT_BOOKING_ID`, sandbox approvals; create: `PAYMENT_PAYLOAD`, `PAYMENT_IDEMPOTENCY_PREFIX`; verify: `PAYMENT_ACTION=verify`, `PAYMENT_VERIFY_PAYLOAD` | payment creation or verification in the provider sandbox only |

`AUTH_USERS_JSON` is an array such as `[{"role":"customer","identifier":"synthetic@example.invalid","password":"..."}]`. Provide enough distinct accounts for the authentication load being tested. `BOOKING_PAYLOAD`, `STAGE_PAYLOAD`, `PAYMENT_PAYLOAD`, and `PAYMENT_VERIFY_PAYLOAD` are the same JSON objects sent by the frontend. Run payment creation and verification as separate controlled smoke runs using actual sandbox output. Never use a real customer account, real payment method, or reusable production record.

## Safety approvals

A remote test requires both `-AllowRemoteTarget` and:

```powershell
$env:PHASE10_REMOTE_APPROVAL='TAILORAHUB_APPROVED_LOAD_TEST'
```

A state-changing suite additionally requires `-AllowSyntheticWrites` and:

```powershell
$env:PHASE10_WRITE_APPROVAL='TAILORAHUB_APPROVED_SYNTHETIC_WRITES'
```

The payment suite also requires:

```powershell
$env:PAYMENT_PROVIDER_MODE='sandbox'
$env:PHASE10_PAYMENT_APPROVAL='TAILORAHUB_APPROVED_SANDBOX_PAYMENTS'
```

Use a staging environment for write, spike, soak, failure, and high-load tests. Obtain explicit AWS/provider approval before generating substantial production traffic.

## Acceptance and reports

The script fails when business errors or HTTP failures reach 1%, read p95 reaches 500 ms, write p95 reaches 1 second, or checks fall to 99%. Each run writes a timestamped JSON result under the ignored `load-test-results/` directory. Copy reviewed, secret-free figures into the Phase 10 evidence record; do not commit raw reports that might expose hosts or test identifiers.
