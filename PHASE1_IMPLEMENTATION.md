# Phase 1 implementation status

## Completed in code

- Bounded list endpoints use `limit=50` and `offset=0` by default, with a maximum page size of 100.
- Customer/tailor orders, booking requests, browse results, notifications, reviews, waiting lists, support tickets, wallet transactions, disputes, and admin collections are bounded.
- Detail collections and CSV exports have explicit safety limits.
- Customer browse counts are pre-aggregated rather than recalculated once per tailor row.
- Follower notifications use one database insert instead of loading every follower and issuing one insert per row.
- Sync and async SQLAlchemy engines have explicit pool, overflow, wait timeout, recycle, statement timeout, and slow-query settings.
- Alembic revision `20260830_0006` adds collection-query indexes. The same indexes exist in `schema.sql` for local `AUTO_MIGRATE` environments.
- Expired OTPs and old expired/revoked refresh sessions are deleted by the scheduled cleanup job.
- `python scripts/check_phase1_query_plans.py` performs a safe, read-only query-plan smoke check without printing connection strings or customer data.

## Production environment defaults

```dotenv
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT_SECONDS=30
DATABASE_POOL_RECYCLE_SECONDS=1800
DATABASE_STATEMENT_TIMEOUT_MS=5000
DATABASE_SLOW_QUERY_MS=500
```

Keep `pool size + overflow`, multiplied by the maximum number of backend processes/containers, below the database connection budget. Recalculate these values before enabling multiple containers.

## Remaining work

Deferred AWS operations are maintained in `PHASE1_PHASE2_PENDING.md`.
