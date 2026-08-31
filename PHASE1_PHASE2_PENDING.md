# Phase 1, Phase 2, Phase 3, and Phase 4 pending items

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
