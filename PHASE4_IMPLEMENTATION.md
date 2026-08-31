# Phase 4 implementation status

## Completed in code

- Added an Amazon SQS task dispatcher with inline local-development mode.
- Added dedicated worker, scheduler, migration, and web container roles.
- Removed database migration and scheduler execution from normal web-container startup.
- Queued email delivery and SMS/OTP delivery without changing secure OTP persistence or verification.
- Added live Amazon SES, SendGrid, SMTP, Twilio, and MSG91 configuration paths.
- Queued idempotent payment-intent reconciliation, wallet reconciliation, booking expiry, OTP cleanup, experience cleanup, media post-processing, and large admin wallet exports.
- Added an idempotency receipt ledger so a retried or duplicated SQS message completes its side effect once.
- Added exponential SQS visibility delays and a CloudFormation template containing an encrypted main queue and DLQ redrive policy.
- Added admin job-status responses with short-lived private report download URLs.
- Added role-aware Docker health checks so workers, schedulers, and migration tasks are not tested as HTTP servers.

## Live email variables for tomorrow

Amazon SES with an ECS IAM task role is recommended for the TailoraHub domain:

```dotenv
EMAIL_PROVIDER=ses
EMAIL_FROM_ADDRESS=TailoraHub <no-reply@your-domain.com>
AWS_SES_REGION=ap-south-1
```

SES does not require an access key in the container when the ECS task role has permission. Verify the domain and production sending access in SES first.

SendGrid alternative:

```dotenv
EMAIL_PROVIDER=sendgrid
EMAIL_API_KEY=add-in-production-secret-store
EMAIL_FROM_ADDRESS=no-reply@your-domain.com
```

SMTP alternative variables already exist: `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURE`, `SMTP_STARTTLS`, `SMTP_USER`, and `SMTP_PASS`.

## Live SMS variables for tomorrow

Twilio:

```dotenv
SMS_PROVIDER=twilio
SMS_API_SECRET=your-account-sid
SMS_API_KEY=your-auth-token
SMS_SENDER_ID=your-approved-sender
```

MSG91:

```dotenv
SMS_PROVIDER=msg91
SMS_API_KEY=add-in-production-secret-store
SMS_SENDER_ID=your-approved-sender-id
SMS_OTP_TEMPLATE_ID=your-approved-template-id
SMS_API_BASE_URL=https://control.msg91.com/api/v5/otp
```

Do not commit the real values. Inject them through the ECS task definition from AWS Secrets Manager or SSM Parameter Store.

## Queue and service variables

```dotenv
TASK_QUEUE_BACKEND=sqs
SQS_TASK_QUEUE_URL=https://sqs.ap-south-1.amazonaws.com/account/tailorahub-production-tasks
SQS_TASK_DLQ_URL=https://sqs.ap-south-1.amazonaws.com/account/tailorahub-production-tasks-dlq
SQS_REGION=ap-south-1
TASK_MAX_ATTEMPTS=5
TASK_VISIBILITY_TIMEOUT_SECONDS=60
TASK_LONG_POLL_SECONDS=20
AUTO_MIGRATE=false
```

Run the same image with exactly one of these roles:

- `SERVICE_ROLE=web`: API container.
- `SERVICE_ROLE=worker`: scalable SQS consumer.
- `SERVICE_ROLE=scheduler`: one desired task that only enqueues scheduled work.
- `SERVICE_ROLE=migration`: one-off deployment task that runs Alembic and exits.

## Remaining production validation

The AWS provisioning, provider activation, real delivery tests, and DLQ test are tracked in `PHASE1_PHASE2_PENDING.md`.

Razorpay webhook signature verification and deduplication remain explicitly assigned to Phase 6; Phase 4 only schedules safe payment-intent reconciliation.
