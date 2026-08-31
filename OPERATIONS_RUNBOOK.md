# TailoraHub production operations runbook

## First response

1. Acknowledge the alert and record its name, transition time, affected environment, and current owner.
2. Open `TailoraHub-production-Operations` and check API errors/latency, running tasks, database, Redis, and queue health together.
3. Search the web, worker, and scheduler log groups using the `requestId` from the failed client response. Never paste authorization headers, OTPs, identity values, or full provider payloads into an incident record.
4. Identify the last deployment and configuration change. Do not make unrelated changes while the incident is active.
5. Prefer a reversible rollback or task replacement. Preserve logs and evidence before changing state.

## Elevated 5xx or unhealthy targets

- Check ALB target health reasons and `/api/health` from inside the approved network.
- Compare the first error time with ECS deployment events and CloudWatch application logs.
- If the current task revision caused the failure, roll the ECS service back to the last healthy task definition and wait for all targets to pass health checks.
- If only one task is unhealthy, let ECS replace it; do not reduce the healthy task count below two.
- Verify a customer read, booking write, and WebSocket tracker after recovery.

## High latency, CPU, or memory

- Check whether traffic, a deployment, database latency, Redis latency, or an external provider changed at the same time.
- Confirm autoscaling is adding tasks and that ALB targets remain healthy.
- Use request route templates and slow-query operation logs to narrow the problem without logging SQL parameters.
- Do not permanently raise task limits or alarm thresholds until Phase 10 evidence identifies the bottleneck.

## Database pressure

- Check RDS CPU, free storage, connections, locks, and RDS Proxy health.
- Stop non-essential exports or reconciliation only through the documented service controls; never terminate arbitrary database sessions without identifying their owner.
- If storage is low, preserve backups and increase allocated storage using the approved change process.
- If failover occurs, verify migration state, write consistency, booking idempotency, and payment records after recovery.

## Redis or real-time failure

- Check Redis CPU, memory, evictions, connections, and TLS endpoint reachability from an ECS task.
- Expect cache misses and controlled API rate-limit degradation; confirm booking data remains authoritative in PostgreSQL.
- Verify WebSocket reconnection and cross-task delivery after Redis recovers.
- Never switch production to process-local cache or real-time state.

## SQS backlog or dead-letter messages

- Check worker running count, oldest message age, application `BackgroundJobFailure`, and worker logs by job ID.
- Inspect a DLQ message only in the authorized AWS console and avoid copying customer payloads externally.
- Fix the root cause before redriving. The job receipt ledger must prevent duplicate side effects.
- Redrive a small sample first, verify results, then continue in controlled batches.

## Payment webhook or provider failure

- Compare `PaymentWebhookFailure` or `ExternalProviderFailure` with provider status and circuit-breaker logs.
- Verify webhook configuration and signature secrets without printing their values.
- Never manually credit a wallet solely because a webhook was received. Reconcile against the gateway transaction and the idempotent payment record.
- Replay only the provider's signed event through the approved tool and verify it completes exactly once.

## Deployment rollback

1. Identify the last healthy immutable ECR tag and ECS task definition revision.
2. Confirm database migrations are backward compatible. If not, follow the reviewed database rollback procedure; never run an unreviewed downgrade in production.
3. Update web and worker services to the last healthy revision. Keep exactly one scheduler service active.
4. Wait for ALB health and ECS steady state, then verify critical customer/tailor flows.
5. Record the failed revision, evidence, rollback time, and follow-up owner.

## Access and ownership

- Production deploy, rollback, database access, secret rotation, billing, and incident-lead roles must be assigned to named people in the private operations system.
- Use individual AWS identities with MFA and least privilege. Do not share the root user or long-lived access keys.
- Rotate exposed or suspected credentials immediately and document what was rotated without recording the secret value.
