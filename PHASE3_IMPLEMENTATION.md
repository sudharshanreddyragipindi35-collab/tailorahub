# Phase 3 implementation status

## Completed in code

- Added a media-storage abstraction with local-development and Amazon S3 production backends.
- Moved profile pictures, portfolio media, offer media, wallet QR images, and dispute photos through that abstraction.
- Added CloudFront-compatible public media URLs.
- Added S3 presigned POST uploads for profile pictures and portfolio media so large files do not pass through backend container memory in production.
- Presigned uploads enforce exact content type, maximum size, owner-specific object prefixes, and post-upload file-signature validation.
- Dispute photos are stored as private objects and returned through short-lived download URLs.
- Production startup fails fast unless S3 storage, a CloudFront media URL, and the Redis real-time backplane are configured.
- Added a dry-run-first legacy media migration script. Existing source files remain untouched for rollback.
- Replaced process-local-only booking event delivery with Redis Pub/Sub while keeping local socket rooms per backend instance.
- Added exponential subscriber reconnection and graceful startup/shutdown cleanup.
- Added short-lived, booking-scoped WebSocket tickets. A signed-in customer or tailor must prove access before obtaining a ticket.
- Retained client reconnect, heartbeat, visibility handling, stale socket cleanup, and slow fallback refresh behaviour.

## Production environment

```dotenv
APP_ENV=production

MEDIA_STORAGE_BACKEND=s3
S3_MEDIA_BUCKET=your-private-media-bucket
S3_MEDIA_REGION=ap-south-1
S3_MEDIA_KEY_PREFIX=media
CLOUDFRONT_MEDIA_BASE_URL=https://media.tailorahub.com
S3_PRESIGN_TTL_SECONDS=300

REALTIME_BACKPLANE=redis
REDIS_URL=rediss://your-valkey-or-redis-endpoint:6379/0
REALTIME_CHANNEL_PREFIX=tailorahub:booking
REALTIME_TICKET_SECONDS=120
```

Do not place AWS access keys in the application environment. Give the ECS task role only the required object permissions under the configured media prefix. Keep the S3 bucket private and let CloudFront access public media through Origin Access Control.

Configure S3 CORS for presigned browser uploads from the approved TailoraHub frontend domains. Permit `POST`, the required form headers, and no unrelated origins.

## Legacy media migration

From `backend`, first run the safe inventory:

```powershell
python scripts/migrate_local_media_to_s3.py
```

After configuring and testing the S3/CloudFront environment, run:

```powershell
python scripts/migrate_local_media_to_s3.py --apply
```

The migration updates database references only after successful uploads and retains local source files for rollback.

## Verification completed

- Backend regression suite passes: 25 tests.
- Frontend production build passes.
- Legacy media migration dry-run passes.
- Two independent connection managers exchanged a booking event through a real temporary Redis 7 container.
- S3 presign conditions, object ownership, content-length limits, MIME checks, and file-signature checks have automated coverage.

## Remaining production validation

1. Provision the private S3 bucket, CloudFront distribution, and Redis/Valkey endpoint.
2. Run the media migration against the production database and verify representative objects.
3. Deploy at least two ECS backend tasks.
4. Keep an active booking tracker open while tasks are added, removed, and rolled over.
5. Confirm uninterrupted events, reconnect behaviour, health output, and CloudFront media delivery.

Scheduler isolation remains part of Phase 4 and is not claimed as Phase 3 work.
