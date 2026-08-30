# Phase 1 and Phase 2 pending items

This file is the single backlog for work intentionally deferred while Phase 3 proceeds.

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
