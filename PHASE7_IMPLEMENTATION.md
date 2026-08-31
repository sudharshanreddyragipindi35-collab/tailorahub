# Phase 7 implementation: AWS production deployment

Phase 7 now has source-controlled deployment definitions for the React frontend and the containerized FastAPI services. The templates do not contain production credentials, account IDs, IP addresses, or resource IDs.

## Included deployment assets

- `amplify.yml` builds the `frontend` workspace with a clean dependency install.
- `customHttp.yml` applies HTTPS, clickjacking, MIME-sniffing, referrer, permissions, and cache headers through Amplify Hosting.
- `deployment/phase7-configure-amplify.ps1` installs the SPA fallback rewrite on the existing Amplify application.
- `deployment/phase7-publish-image.ps1` creates an immutable, scan-on-push ECR repository when required, then builds and pushes a commit-tagged backend image.
- `deployment/phase7-ecs-cloudformation.yml` creates the ALB, private Fargate services, task roles, security groups, health checks, rolling rollback, logs, and CPU/memory target tracking.
- `deployment/phase7-ecs-parameters.example.json` records every required non-secret stack input without committing live values.

## Required existing AWS resources

The Phase 7 stack deliberately connects to existing resources instead of creating duplicate stateful services:

1. A VPC with two public ALB subnets and two private application subnets.
2. An ACM certificate for `api.tailorahub.com` in the ECS/ALB region.
3. RDS PostgreSQL behind RDS Proxy, reachable from the application security group on port 5432.
4. Private ElastiCache Redis/Valkey, reachable on port 6379 using TLS.
5. The Phase 3 S3 media bucket and CloudFront media domain.
6. The Phase 4 SQS task queue and dead-letter queue.
7. NAT access or the necessary VPC endpoints for ECR, CloudWatch Logs, S3, SQS, and Secrets Manager.

## Secrets Manager layout

Create one JSON secret such as `tailorahub/production/application` with these keys:

```json
{
  "DATABASE_URL": "postgresql+psycopg://USER:PASSWORD@RDS_PROXY_HOST:5432/DATABASE",
  "JWT_SECRET": "GENERATE_A_LONG_RANDOM_VALUE",
  "JWT_REFRESH_SECRET": "GENERATE_A_DIFFERENT_LONG_RANDOM_VALUE",
  "ADMIN_PASSWORD": "GENERATE_A_STRONG_UNIQUE_PASSWORD",
  "AADHAAR_ENCRYPTION_KEY": "GENERATE_THE_APPLICATION_SUPPORTED_KEY"
}
```

When live SMS, email, and Razorpay credentials arrive, create a separate JSON secret such as `tailorahub/production/providers` containing all six keys below. A value may be empty only while its matching provider remains `mock`.

```json
{
  "SMS_API_KEY": "",
  "SMS_API_SECRET": "",
  "EMAIL_API_KEY": "",
  "RAZORPAY_KEY_ID": "",
  "RAZORPAY_KEY_SECRET": "",
  "RAZORPAY_WEBHOOK_SECRET": ""
}
```

Never add either live JSON document to this repository. Pass only the secret ARNs to CloudFormation.

## Deployment order

1. Copy `deployment/phase7-ecs-parameters.example.json` outside the repository and replace every placeholder.
2. Run `deployment/phase7-publish-image.ps1`; copy its immutable `ImageUri` into the parameter file.
3. Validate and deploy `deployment/phase7-ecs-cloudformation.yml` with `CAPABILITY_NAMED_IAM` and `DeployServices=false`. This creates the foundation and task definitions without starting application traffic.
4. Run the output `MigrationTaskDefinitionArn` once in the output cluster, private subnets, and application security group. Wait for exit code `0`.
5. Update the stack with the same parameters and `DeployServices=true`. The web, worker, and single scheduler services start only after migration succeeds.
6. Point the `api.tailorahub.com` DNS record at the ALB, then deploy the Phase 5 WAF template using the ALB ARN output.
7. Set Amplify environment variables `VITE_API_BASE=https://api.tailorahub.com/api` plus the approved public-only browser keys, deploy the frontend, and run `deployment/phase7-configure-amplify.ps1`.
8. Check `/api/health`, task health, CloudWatch logs, worker queue consumption, the single scheduler replica, and an end-to-end customer/tailor flow.

Example stack commands (replace the parameter file path with the private completed copy):

```powershell
aws cloudformation validate-template --profile tailorahub-prod --region ap-south-1 --template-body file://deployment/phase7-ecs-cloudformation.yml
aws cloudformation deploy --profile tailorahub-prod --region ap-south-1 --stack-name tailorahub-production-application --template-file deployment/phase7-ecs-cloudformation.yml --parameter-overrides file://C:/PRIVATE-PATH/phase7-ecs-parameters.json --capabilities CAPABILITY_NAMED_IAM
```

The two backend web tasks start at 1 vCPU and 2 GB each. Target tracking starts at 60% CPU and 70% memory, with a minimum of two and maximum of ten web tasks. These values must be tuned from Phase 10 load-test evidence.
