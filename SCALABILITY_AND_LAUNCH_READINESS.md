# TailoraHub Scalability and Launch Readiness Plan

## Purpose

This document records the scalability, performance, reliability, and infrastructure work that must be completed **after the planned UI and backend features are finished, but before the public production launch**.

The goal is to ensure TailoraHub can grow from an initial launch to thousands of registered and concurrently active users without depending on one server or loading excessive data into the browser.

> Important: No system can guarantee that it will never slow down. Production readiness must be demonstrated through monitoring and repeatable load tests. Infrastructure must then scale according to measured traffic.

## Target architecture

```text
Users
  |
  v
Amplify / CloudFront (frontend)
  |
  v
AWS WAF + Application Load Balancer
  |
  v
ECS backend containers (minimum 2, automatically scalable)
  |-- RDS PostgreSQL + RDS Proxy
  |-- ElastiCache Redis/Valkey
  |-- Amazon S3 media storage
  |-- SQS background queues
  `-- Dedicated scheduler and background workers
```

## Launch requirement

Do not declare the application ready for a large public launch until the mandatory sections in this document are completed and the final load-test gate passes.

## Phase 1: API and database performance

- [x] Add server-side pagination to every potentially large collection (default 50, maximum 100; bounded detail/export collections).
- [x] Paginate customer orders.
- [x] Paginate tailor orders and booking requests.
- [x] Paginate tailor search and browse results.
- [x] Paginate notifications and updates.
- [x] Paginate reviews, wallet transactions, waiting-list records, support tickets, and admin lists.
- [ ] Prefer cursor pagination for records ordered by date or ID.
- [x] Never return an unlimited collection from a production endpoint.
- [x] Return summary records in list endpoints and load full details only when opened.
- [x] Review PostgreSQL query plans for the most frequently used endpoints (repeatable read-only check: `backend/scripts/check_phase1_query_plans.py`).
- [x] Add compound indexes that match real customer-order, tailor-order, slot, payment, notification, review, and support queries.
- [x] Remove repeated per-row count queries and other N+1 query patterns.
- [x] Configure slow-query logging at a configurable threshold (`DATABASE_SLOW_QUERY_MS`, default 500 ms).
- [x] Archive or expire old operational data when appropriate (expired OTP and refresh-session cleanup).
- [ ] Consider table partitioning only when measured table growth justifies it.

### Database connection management

- [x] Consolidate application database access around explicitly configured sync/async engine and session lifecycles.
- [x] Configure connection pool size, maximum overflow, connection timeout, query timeout, and pool recycle.
- [ ] Use RDS Proxy when multiple backend containers are enabled.
- [ ] Keep total application connections safely below the PostgreSQL connection limit.
- [ ] Store database credentials in AWS Secrets Manager, not source files or images.
- [ ] Enable automated backups.
- [ ] Perform and document a database restore test.

## Phase 2: Frontend performance

- [ ] Remove aggressive 5-second and 15-second polling where real-time events can be used.
- [ ] Use WebSockets for active booking, tracker, payment, and measurement updates.
- [ ] Use fallback polling only after WebSocket failure and at a slower interval.
- [ ] Re-fetch or update local state immediately after successful create, update, delete, approve, reject, or payment operations.
- [ ] Refresh relevant data when the browser becomes visible again.
- [ ] Lazy-load dashboard pages and infrequently used components.
- [ ] Split the production JavaScript bundle by route/page.
- [ ] Avoid loading full order details for every collapsed order card.
- [ ] Use list virtualization if a screen must display many records.
- [ ] Optimize images as WebP/AVIF and provide appropriate responsive sizes.
- [ ] Cache immutable frontend assets with content-hashed file names.
- [ ] Verify performance on average Android phones and slower mobile networks.

## Phase 3: Stateless and horizontally scalable backend

- [ ] Make backend containers stateless.
- [ ] Do not store required application state only in Python process memory.
- [ ] Do not store permanent uploaded media on a container filesystem.
- [ ] Store profile pictures, portfolio media, support attachments, and other uploads in Amazon S3.
- [ ] Use validated presigned upload/download URLs where appropriate.
- [ ] Serve public media through CloudFront.
- [ ] Enforce file size, MIME type, extension, and authorization checks.

### Shared real-time events

- [ ] Replace process-local-only WebSocket broadcasting with Redis/Valkey Pub/Sub or an equivalent shared event layer.
- [ ] Ensure an event published by one backend container reaches clients connected to every other container.
- [ ] Implement WebSocket reconnect, heartbeat, stale-connection cleanup, and authorization.
- [ ] Verify WebSocket behaviour while ECS tasks are added, removed, or redeployed.

## Phase 4: Background processing

Move operations that do not need to block the user request into SQS-backed workers.

- [ ] Queue email delivery.
- [ ] Queue SMS and OTP-provider delivery while retaining secure OTP state handling.
- [ ] Queue non-critical notifications.
- [ ] Queue image/media processing.
- [ ] Queue reports and exports.
- [ ] Queue payment reconciliation and safe webhook retries.
- [ ] Queue wallet reconciliation.
- [ ] Configure retry limits and exponential backoff.
- [ ] Configure a dead-letter queue for failed jobs.
- [ ] Make every retried job idempotent.

### Scheduler isolation

- [ ] Run scheduled jobs in one dedicated scheduler/worker service.
- [ ] Do not start an independent scheduler inside every web container.
- [ ] Move database migrations out of normal multi-replica web startup.
- [ ] Run migrations once as a controlled deployment task.
- [ ] Prevent duplicate booking-expiry, notification, reconciliation, and cleanup jobs.

## Phase 5: Caching and traffic protection

- [ ] Use ElastiCache Redis/Valkey for safe short-lived caching.
- [ ] Cache frequently viewed, slowly changing tailor summaries and service data.
- [ ] Invalidate or refresh cached values after updates.
- [ ] Do not cache user-private responses under shared keys.
- [ ] Add API rate limiting by IP and authenticated user.
- [ ] Apply strict limits to login, registration, forgot-password, OTP, payment, and upload endpoints.
- [ ] Add AWS WAF managed protection and rate-based rules.
- [ ] Return clear `429 Too Many Requests` responses when a limit is reached.
- [ ] Add request body and upload size limits.

## Phase 6: External integrations and failure isolation

Every external service call must have controlled failure behaviour.

- [ ] Configure short connection and response timeouts.
- [ ] Retry only operations that are safe to retry.
- [ ] Use exponential backoff with jitter.
- [ ] Use idempotency keys for booking creation, payment creation, payment webhooks, and other sensitive writes.
- [ ] Verify Razorpay webhook signatures.
- [ ] Deduplicate webhook processing.
- [ ] Implement circuit-breaker behaviour for unstable external providers.
- [ ] Ensure slow SMS, email, maps, or payment providers cannot freeze unrelated application requests.
- [ ] Record provider errors without exposing secrets to users or logs.

## Phase 7: AWS production deployment

The initial sizes below are starting hypotheses and must be adjusted using load-test results.

### Frontend

- [ ] Deploy the production frontend through AWS Amplify/CloudFront.
- [ ] Configure SPA rewrites so refreshed application routes return `index.html`.
- [ ] Configure secure response headers and cache policies.

### Backend

- [ ] Store the backend image in Amazon ECR.
- [ ] Deploy the backend using ECS Fargate.
- [ ] Run at least two backend tasks in production.
- [ ] Place tasks behind an Application Load Balancer.
- [ ] Configure health and readiness checks.
- [ ] Start testing with approximately 1 vCPU and 2 GB memory per task.
- [ ] Configure automatic scaling with an initial minimum of 2 and maximum of 10 tasks.
- [ ] Start with CPU target near 60% and memory target near 70%, then tune from measurements.
- [ ] Consider ALB request-count or active-connection scaling after collecting real metrics.
- [ ] Use rolling or blue/green deployment with health verification.

### Data services

- [ ] Use RDS PostgreSQL in private subnets.
- [ ] Use Multi-AZ for the public production launch when the availability requirement justifies it.
- [ ] Use RDS Proxy for pooled database access.
- [ ] Use ElastiCache Redis/Valkey in private subnets.
- [ ] Use S3 for permanent uploaded media.
- [ ] Use SQS for background work.
- [ ] Restrict security groups to only required service-to-service traffic.

## Phase 8: Monitoring, alerting, and operations

- [ ] Enable structured application logs with request IDs.
- [ ] Enable CloudWatch logs for backend, worker, scheduler, and load balancer.
- [ ] Enable ECS Container Insights.
- [ ] Monitor request rate, latency, error rate, CPU, memory, task count, restarts, and unhealthy targets.
- [ ] Monitor PostgreSQL CPU, storage, connections, locks, slow queries, and replica lag when applicable.
- [ ] Monitor Redis memory, evictions, connections, and latency.
- [ ] Monitor SQS queue depth, oldest message age, retries, and dead-letter messages.
- [ ] Create alarms for elevated 4xx/5xx errors, latency, CPU, memory, unhealthy tasks, database saturation, and payment/webhook failures.
- [ ] Configure an operational notification channel for critical alarms.
- [ ] Create runbooks for common incidents.
- [ ] Define who can deploy, roll back, access production data, and rotate secrets.

## Phase 9: Security and privacy review

- [ ] Keep secrets out of Git, frontend bundles, ZIP files, Docker images, screenshots, and logs.
- [ ] Rotate any secret that was previously exposed.
- [ ] Encrypt production traffic with HTTPS.
- [ ] Encrypt RDS, Redis, S3, backups, and secrets at rest.
- [ ] Apply least-privilege IAM permissions.
- [ ] Validate authorization for every customer, tailor, and admin record operation.
- [ ] Review logging for phone numbers, addresses, payment references, OTPs, and identity data.
- [ ] Add data retention and account deletion procedures.
- [ ] Complete a dependency and container vulnerability scan.
- [ ] Complete a pre-launch security review.

## Phase 10: Load and resilience testing

### Required test scenarios

- [ ] Authentication and session refresh.
- [ ] Browse and search tailors.
- [ ] Open a tailor profile.
- [ ] Load services, reviews, offers, favorites, and follower data.
- [ ] Preview and submit a booking.
- [ ] Prevent duplicate booking submission.
- [ ] Load customer and tailor order lists.
- [ ] Update booking stages.
- [ ] Track an active order through WebSockets.
- [ ] Create and verify payments safely in the correct test environment.
- [ ] Process notifications.
- [ ] Upload and download media.
- [ ] Exercise admin reports and dashboards separately from customer traffic.

### Test levels

- [ ] Baseline test: 50 concurrent users.
- [ ] Normal-load test: 100 concurrent users.
- [ ] Growth test: 250 concurrent users.
- [ ] Release test: 500 concurrent users.
- [ ] High-load test: 1,000 concurrent users.
- [ ] Continue toward 5,000 concurrent users only after every preceding level passes.
- [ ] Spike test with a sudden traffic increase.
- [ ] Soak test for several hours to detect memory, connection, and resource leaks.
- [ ] Failure test while replacing or terminating a backend task.
- [ ] Database failover and backup-restore test.

### Initial acceptance targets

- [ ] API error rate remains below 1% during the approved target load.
- [ ] Normal read endpoint p95 response time remains below 500 ms.
- [ ] Normal booking/write endpoint p95 remains below 1 second, excluding unavoidable external-provider interaction.
- [ ] No duplicate booking, payment, notification, or scheduler actions occur.
- [ ] WebSocket events work across all backend replicas.
- [ ] Database CPU normally remains below approximately 70%.
- [ ] Database connections remain below approximately 70-80% of the configured safe limit.
- [ ] Backend containers recover automatically when one becomes unhealthy.
- [ ] The system remains usable during a deployment.

## Production service objectives

The final service objectives should be confirmed using measured performance.

- Availability target: 99.9% per month.
- Normal API p95 latency target: below 500 ms.
- Normal write p95 latency target: below 1 second, excluding external checkout pages.
- Error-rate target: below 1%.
- Minimum production backend task count: 2.
- Recovery objective: an unhealthy task is automatically replaced without a full outage.
- Data integrity objective: no duplicate or partially committed booking/payment operations.

## Implementation order

Complete the work in this sequence:

1. Finish and stabilize planned UI and backend features.
2. Add pagination and optimize database queries.
3. Reduce frontend polling and implement reliable shared real-time updates.
4. Move permanent media to S3/CloudFront.
5. Add Redis/Valkey for shared events and carefully selected caching.
6. Add SQS workers and isolate scheduled jobs.
7. Configure database pooling and RDS Proxy compatibility.
8. Add rate limiting, WAF protection, monitoring, and alarms.
9. Deploy multiple ECS backend tasks behind an ALB.
10. Run progressive load and resilience tests.
11. Tune ECS, RDS, Redis, and application settings from test evidence.
12. Complete security, backup/restore, and launch reviews.

## Final go-live gate

Production launch approval should require all of the following:

- [ ] Planned UI and backend functionality is complete.
- [ ] Automated functional tests pass.
- [ ] Database migrations are reviewed and tested.
- [ ] Pagination is enabled for every large collection.
- [ ] Permanent uploads use S3 rather than container-local storage.
- [ ] Multiple backend tasks can operate without losing real-time events.
- [ ] Scheduled and background jobs cannot execute more than intended.
- [ ] Monitoring dashboards and critical alarms are active.
- [ ] Backups and a restore procedure are verified.
- [ ] Security and privacy review is complete.
- [ ] The agreed target load passes all acceptance criteria.
- [ ] A rollback procedure is documented and tested.

## Ongoing work after launch

- Review performance and error dashboards regularly.
- Repeat load tests after significant application or infrastructure changes.
- Review slow queries and database growth each month.
- Review capacity before promotions or large onboarding events.
- Patch dependencies and base images regularly.
- Test backups and disaster recovery on a defined schedule.
- Increase or reduce infrastructure only according to measured demand.
