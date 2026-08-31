# Phase 1 through Phase 8 pending items

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

## Phase 7: AWS account deployment and production validation

1. Create or confirm two public ALB subnets and two private application subnets with NAT access or the required VPC endpoints.
2. Issue and validate the regional ACM certificate for `api.tailorahub.com`.
3. Create the application and optional provider JSON secrets described in `PHASE7_IMPLEMENTATION.md`; pass only their ARNs to ECS.
4. Publish an immutable commit-tagged backend image with `deployment/phase7-publish-image.ps1` and review the ECR scan result before deployment.
5. Replace every placeholder in a private copy of `deployment/phase7-ecs-parameters.example.json`, validate the template, and deploy `deployment/phase7-ecs-cloudformation.yml` with `CAPABILITY_NAMED_IAM`.
6. Run the migration task once and require exit code `0` before allowing the new web, worker, and scheduler revisions to serve production traffic.
7. Confirm both web tasks become healthy behind the ALB, both worker tasks consume SQS jobs, and exactly one scheduler task remains active.
8. Point `api.tailorahub.com` to the ALB and associate `deployment/phase5-waf-cloudformation.yml` with the ALB ARN.
9. Add `VITE_API_BASE=https://api.tailorahub.com/api` and approved browser-only keys to Amplify, then deploy the frontend using `amplify.yml`.
10. Run `deployment/phase7-configure-amplify.ps1` and verify direct refreshes of customer, tailor, and private admin routes return the React application rather than a 404 or blank screen.
11. Verify the production security headers and immutable asset/no-cache HTML policies from the public domain.
12. Test a rolling ECS deployment and an unhealthy-task replacement while requests and WebSocket tracking remain active.
13. Generate controlled load to confirm scaling from two tasks and back down without dropping below two; tune CPU, memory, and cooldown settings from evidence.
14. Confirm RDS Proxy, Redis TLS, private S3 media, CloudFront delivery, SQS/DLQ, security-group boundaries, and approved `/32` admin access work from the deployed services.

The Phase 7 infrastructure source and ordered production runbook are documented in `PHASE7_IMPLEMENTATION.md`.

## Phase 8: production monitoring and operational validation

1. Replace every placeholder in a private copy of `deployment/phase8-parameters.example.json` with the real ALB, target group, ECS, RDS, Redis, and SQS CloudWatch dimensions.
2. Reauthenticate `tailorahub-prod`, validate `deployment/phase8-observability-cloudformation.yml` in AWS, and deploy the observability stack.
3. Confirm the SNS operations subscription and send one controlled alarm plus recovery notification to verify the channel end to end.
4. Add the Phase 8 `AlbAccessLogsBucketName` output to the Phase 7 parameters, update the application stack, and verify ALB log objects arrive under the expected account prefix.
5. Deploy the Phase 8 backend image and confirm valid JSON logs, `X-Request-ID` correlation, EMF extraction, log-group retention, and safe absence of bodies, headers, OTPs, identity values, and provider secrets.
6. Verify every alarm uses the correct production dimensions and is not stuck in `INSUFFICIENT_DATA` because of an identifier or metric mismatch.
7. Replace the initial RDS and Redis connection thresholds with values derived from actual instance limits and the Phase 1 connection budget.
8. Generate representative traffic and tune ALB, ECS, RDS, Redis, SQS, and application thresholds after measuring normal, peak, and quiet periods.
9. Run controlled unhealthy-task, high-latency, queue-backlog, DLQ, provider-failure, and payment-webhook drills using `OPERATIONS_RUNBOOK.md`.
10. Confirm the CloudWatch dashboard and incident queries are usable by the people responsible for production without granting unnecessary data or infrastructure access.
11. Assign named owners for deploys, rollbacks, database access, secret rotation, billing, alert response, and incident leadership in the private operations system.
12. Review monitoring cost, log retention, alarm noise, and SNS delivery monthly, preserving security and payment alarms even during tuning.

The Phase 8 source implementation, deployment order, alarms, and operational procedures are documented in `PHASE8_IMPLEMENTATION.md` and `OPERATIONS_RUNBOOK.md`.
