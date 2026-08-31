# Phase 10 implementation: load and resilience testing

Phase 10 adds a guarded, repeatable k6 harness and an evidence-driven runbook. Source automation is complete; the AWS load runs, resilience drills, measurements, and capacity tuning are intentionally retained in `PHASE1_PHASE2_PENDING.md` until they are executed against an approved staging or production-like environment.

## Implemented test coverage

- Public health, browse, search result, profile-service, customer, tailor, and private admin read paths.
- Authentication followed by refresh using dedicated synthetic accounts.
- Booking preview/create and a same-key replay that must return `duplicate: true`.
- Customer/tailor order and notification payloads, controlled stage updates, media transfer, and sandbox-only payment creation.
- Booking tracker ticket creation and WebSocket ping/pong validation.
- Smoke, 50, 100, 250, 500, 1,000, spike, and configurable multi-hour soak profiles.
- Release thresholds for error rate, checks, read p95, and write p95.
- Separate admin traffic and fail-closed approvals for remote, write, and payment tests.
- Timestamped local JSON evidence excluded from Git.

The harness follows the k6 scenario/lifecycle and threshold model and keeps response bodies discarded except where token/idempotency assertions require them. This reduces load-generator memory pressure at higher concurrency.

## Ordered execution

1. Use an isolated staging environment with the production ECS, ALB, RDS Proxy, RDS, Redis, SQS, S3/CloudFront, WAF, and monitoring topology.
2. Create dedicated synthetic customer/tailor/admin users, services, bookings, media objects, and sandbox payment records. Exclude real personal data.
3. Run `public-read` and authenticated read smoke tests. Resolve every functional failure before load increases.
4. Run 50, 100, 250, 500, then 1,000 concurrent users. Stop at the first failed threshold or infrastructure alarm; do not jump directly to a higher level.
5. Run booking/idempotency, notifications, media, WebSocket, and payment-sandbox suites at controlled traffic levels. Reconcile database and queue records for duplicates.
6. Run admin reads separately from a source IP allowed by `ADMIN_ALLOWED_NETWORKS`; do not expose or bypass the private admin network rule.
7. Run the spike profile, then a four-hour-or-longer soak while observing ECS CPU/memory/restarts, ALB latency/5xx, RDS CPU/connections/locks, Redis evictions, and SQS age/backlog/DLQ.
8. During a stable read/WebSocket run, force one ECS web task replacement and then a rolling deployment. Confirm traffic and tracking remain available.
9. In an isolated recovery window, perform the approved RDS failover and snapshot restore procedures. Never perform an unplanned destructive database drill against live customer traffic.
10. Record results, bottlenecks, changes, owners, and rerun evidence. Proceed toward 5,000 users only after all earlier profiles pass and the load generator itself has spare CPU/network capacity.

## Acceptance gate

- HTTP and business error rates remain below 1%.
- Normal read p95 remains below 500 ms and normal write p95 remains below 1 second, excluding measured provider latency.
- Duplicate booking/payment/job records remain zero after replay and concurrency tests.
- WebSockets work across replicas and survive task replacement/rolling deployment.
- RDS CPU is normally below approximately 70%; connections remain below 70-80% of the approved safe budget.
- Redis has no evictions, queues drain after load, containers remain stable, alarms fire correctly, and the service recovers from controlled failures.
- Every profile has a reviewed, secret-free result record and capacity conclusion.

The thresholds are initial release targets, not proof of capacity. Only measured runs against the exact release and representative infrastructure can close Phase 10.
