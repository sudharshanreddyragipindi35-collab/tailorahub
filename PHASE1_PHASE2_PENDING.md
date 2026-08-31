# Phase 1 through Phase 6 pending items

This file is the single backlog for production-account work and measured validation intentionally deferred while implementation continues.

## Phase 1: production database and AWS operations

These require changes or measurements in the production AWS account:

1. Move database credentials to AWS Secrets Manager and inject `DATABASE_URL` at runtime.
2. Enable and verify automated RDS backups.
3. Restore an RDS snapshot into an isolated database and record the restore result.
4. Add RDS Proxy before running multiple backend containers.
5. Recalculate the total database connection budget for the selected RDS instance, worker count, and ECS task count.
6. Add opaque cursor pagination only if production measurements show that deep offset pagination is required.

## Phase 2: measured device validation

1. Test the deployed production build on an average Android phone.
2. Repeat the test with a throttled mobile connection.
3. Record Core Web Vitals and address any measured regression before public launch.

The source-code portions of Phases 1 and 2 are documented in `PHASE1_IMPLEMENTATION.md` and `PHASE2_IMPLEMENTATION.md`.

## Phase 3: AWS provisioning and rolling validation

1. Provision the private S3 media bucket and CloudFront distribution with Origin Access Control.
2. Provision the shared Redis/Valkey endpoint and inject its TLS URL into the backend tasks.
3. Run the legacy media migration against production and verify representative profile, portfolio, QR, offer, and dispute objects.
4. Deploy at least two ECS backend tasks.
5. Keep an active booking tracker open while tasks are added, removed, and replaced.
6. Confirm uninterrupted WebSocket events, reconnect behaviour, health output, private attachment access, and CloudFront delivery.

The Phase 3 source implementation and required environment variables are documented in `PHASE3_IMPLEMENTATION.md`.

## Phase 4: AWS queues and live communication providers

1. Deploy `deployment/phase4-sqs-cloudformation.yml` and attach least-privilege SQS permissions to the ECS task roles.
2. Run Alembic once with `SERVICE_ROLE=migration` before starting the Phase 4 workers.
3. Deploy separate `web`, `worker`, and single-instance `scheduler` ECS services.
4. Add the verified domain email and live SMS environment values when the provider credentials arrive.
5. Send real email and SMS OTP tests, without placing provider keys in Git or Docker images.
6. Force one safe test job to exceed its retry limit and confirm it reaches the DLQ with no duplicate delivery.

The Phase 4 implementation and provider-variable templates are documented in `PHASE4_IMPLEMENTATION.md`.

## Phase 5: AWS traffic protection and measured tuning

1. Set `TRAFFIC_STORE_BACKEND=redis` and point `REDIS_URL` at the shared ElastiCache/Valkey endpoint.
2. Set `CLIENT_IP_TRUSTED_PROXY_NETWORKS` to only the actual ALB/VPC proxy CIDRs, then verify the application records the real public client IP.
3. Deploy `deployment/phase5-waf-cloudformation.yml` against the production backend ALB.
4. Associate a CloudFront-scope WAF web ACL with the public Amplify/CloudFront frontend where the selected Amplify plan and region support it.
5. Exercise login, OTP, payment, upload, and ordinary API limits and confirm clear `429` responses and `Retry-After` headers.
6. Send an oversized normal request and upload and confirm both are rejected with `413` before endpoint processing.
7. Verify cache `HIT`/`MISS` behaviour and invalidation while requests alternate between at least two backend tasks.
8. Review CloudWatch/WAF samples after representative traffic and tune limits without weakening OTP, authentication, payment, or upload protection.

The Phase 5 source implementation and environment-variable templates are documented in `PHASE5_IMPLEMENTATION.md`.

## Phase 6: live-provider and webhook validation

1. Add the production `RAZORPAY_WEBHOOK_SECRET` through AWS Secrets Manager or SSM, never Git or a Docker image.
2. Register `https://api.tailorahub.com/api/v1/payments/webhooks/razorpay` in the Razorpay dashboard for `payment.captured` and `order.paid` events.
3. Run signed sandbox events followed by one real low-value payment and confirm the booking, payment intent, tailor wallet, and admin wallet update exactly once.
4. Replay an identical event, send an invalid signature, and deliver supported events out of order; verify deduplication and no duplicate wallet credit or notification.
5. Activate real email and SMS credentials when available and measure provider latency, timeout, queue retry, DLQ, and circuit-open behaviour.
6. Select and implement the production Aadhaar KYC provider only after its compliance, consent, data-retention, and API requirements are approved.
7. Select and implement a live payout provider only after settlement, reconciliation, and beneficiary-verification requirements are approved.
8. Run controlled provider-failure tests and confirm slow email, SMS, Razorpay, KYC, and payout services do not affect unrelated API requests.
9. Review production logs and traces to confirm URLs, authorization headers, OTPs, Aadhaar values, API keys, secrets, and full provider payloads are not recorded.

The Phase 6 source implementation and production variables are documented in `PHASE6_IMPLEMENTATION.md`.
