# Phase 8 implementation: monitoring, alerting, and operations

Phase 8 adds traceable JSON application logs, low-cardinality application failure metrics, a production operations dashboard, actionable alarms, an encrypted alert topic, ALB log storage, and an incident runbook. No production email address, AWS identifier, or account credential is committed.

## Application observability

`backend/app/observability.py` configures one JSON object per log line. `backend/logging.json` applies the same formatter to Uvicorn while the duplicate text access log is disabled. Each HTTP request receives an `X-Request-ID`; a valid caller-supplied ID is preserved so the same identifier can be followed from the client into CloudWatch. Background workers use the queue job ID as their request context.

The HTTP completion log includes only method, route template, status, and duration. It deliberately excludes query strings, request/response bodies, authorization headers, cookies, phone numbers, and network addresses.

CloudWatch Embedded Metric Format records use namespace `TailoraHub/Application`:

- `Http5xx`
- `ExternalProviderFailure`
- `PaymentWebhookFailure`
- `BackgroundJobFailure`

Production ECS tasks set `CLOUDWATCH_EMF_ENABLED=true`. Local development keeps it disabled by default.

## AWS monitoring stack

`deployment/phase8-observability-cloudformation.yml` creates:

- an encrypted SNS operations topic and optional email subscription;
- an encrypted, private, versioned ALB access-log bucket with 90-day retention;
- ALB 5xx, target 5xx, p95 latency, and unhealthy-target alarms;
- ECS CPU, memory, and minimum-running-task alarms;
- RDS CPU, connection, and free-storage alarms;
- Redis/Valkey CPU, connection, and eviction alarms;
- SQS depth, message-age, and dead-letter alarms;
- application 5xx, external-provider, payment-webhook, and background-job alarms;
- one CloudWatch dashboard for API, ECS, RDS, Redis, SQS, application metrics, and recent JSON errors.

The thresholds are safe starting hypotheses. Replace the connection thresholds with values derived from the selected RDS and Redis sizes, then tune all thresholds after representative Phase 10 tests.

## Deployment order

1. Copy `deployment/phase8-parameters.example.json` outside the repository and replace every placeholder with the real production dimension.
2. Refresh the AWS CLI session and validate `deployment/phase8-observability-cloudformation.yml`.
3. Deploy the stack with the private parameter file.
4. Confirm the SNS email subscription. An unconfirmed subscription receives no alarm messages.
5. Copy the `AlbAccessLogsBucketName` output into the Phase 7 application parameters and update the Phase 7 stack so ALB access logging is enabled.
6. Deploy a new backend image containing Phase 8, then verify JSON records and EMF metrics appear in CloudWatch Logs.
7. Exercise one controlled test alarm and confirm both `ALARM` and recovery notifications reach the operations channel.
8. Follow `OPERATIONS_RUNBOOK.md` during failure drills and record the results in the private operations system.

Example commands:

```powershell
aws cloudformation validate-template --profile tailorahub-prod --region ap-south-1 --template-body file://deployment/phase8-observability-cloudformation.yml
aws cloudformation deploy --profile tailorahub-prod --region ap-south-1 --stack-name tailorahub-production-observability --template-file deployment/phase8-observability-cloudformation.yml --parameter-overrides file://C:/PRIVATE-PATH/phase8-parameters.json
```

The Phase 8 stack creates monitoring resources only. It does not restart ECS, change the database, purge queues, or publish customer data.
