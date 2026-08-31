# Phase 9 implementation: security and privacy review

Phase 9 adds source-level controls that fail closed in production and a repeatable security-review path. It does not claim that AWS account encryption, credential rotation, scanning of the exact immutable ECR release, or an independent review has occurred; those measured/account-level tasks remain in `PHASE1_PHASE2_PENDING.md`.

## Implemented controls

- Production startup rejects demo data, plaintext admin-credential output, runtime-generated/placeholder secrets, shared access/refresh JWT secrets, plaintext PostgreSQL/Redis connections, wildcard or non-HTTPS CORS, missing admin CIDRs, and incomplete S3/CloudFront/SQS/Redis configuration.
- Demo tailor seeding is local-only by default. The admin credential note is local-only by default and excluded from Git and Docker.
- API responses receive no-store, CSP, clickjacking, MIME-sniffing, referrer, permissions, and resource-policy headers; HSTS is enabled in production.
- Amplify receives a CSP compatible with the current API, WebSocket tracker, Google Maps, fonts, and Razorpay integrations.
- Customer and tailor deletion revoke sessions, request media deletion, clear identity/authentication fields, and leave pseudonymized business records only after active-order/payment safety checks.
- The repository scanner rejects tracked keys, credential files, deployment archives, common live-token formats, and secret-shaped `VITE_` variables.
- GitHub Actions run Gitleaks, `pip-audit`, `npm audit`, and a HIGH/CRITICAL Trivy container scan on protected branches and weekly.
- `SECURITY.md` and `DATA_RETENTION_AND_DELETION.md` define private reporting and the controlled deletion process.

Local verification on 31 August 2026 passed 51 backend tests, the production frontend build, the repository secret-hygiene check, `pip-audit`, `npm audit`, and a Trivy scan with zero HIGH/CRITICAL findings after refreshing the Debian base packages. The exact immutable ECR release must still pass the same workflow before deployment.

## Production configuration changes

Set these values explicitly in every production task:

```dotenv
ENABLE_DEMO_DATA=false
WRITE_ADMIN_CREDENTIAL_FILE=false
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@RDS_PROXY_HOST:5432/DATABASE?sslmode=require
REDIS_URL=rediss://REDIS_ENDPOINT:6379/0
```

The application secret must contain unique random `JWT_SECRET`, `JWT_REFRESH_SECRET`, `ADMIN_PASSWORD`, and `AADHAAR_ENCRYPTION_KEY` values. Keep them in AWS Secrets Manager. A rotated secret is picked up by ECS only after a new task starts, so force a controlled deployment after rotation.

## Release gate

Before public launch, complete every Phase 9 item in the consolidated pending file: rotate any previously exposed credential, verify TLS and encryption in AWS, review IAM and authorization, run the workflow against the exact release, test deletion and media removal in production, approve retention periods, and complete an independent pre-launch security review.
