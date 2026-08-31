# TailoraHub domain email configuration

The application now chooses a verified sender alias by message purpose:

| Purpose | Sender |
| --- | --- |
| Default | `noreply@tailorahub.com` |
| Verification and OTP | `verify@tailorahub.com` |
| Booking notifications | `bookings@tailorahub.com` |
| Support | `support@tailorahub.com` |
| Payments | `payments@tailorahub.com` |
| Admin | `admin@tailorahub.com` |

Set these values in the backend production environment (or ECS task secrets),
not in Git. The mailbox password/API key must never be committed:

```dotenv
EMAIL_PROVIDER=smtp
SMTP_HOST=<your-mail-provider-smtp-host>
SMTP_PORT=587
SMTP_STARTTLS=true
SMTP_SECURE=false
SMTP_USER=sudharshan.r@tailorahub.com
SMTP_PASS=<secret-in-AWS-Secrets-Manager-or-SSM>
EMAIL_FROM_ADDRESS=TailoraHub <noreply@tailorahub.com>
EMAIL_FROM_DEFAULT=TailoraHub <noreply@tailorahub.com>
EMAIL_FROM_VERIFY=TailoraHub Verify <verify@tailorahub.com>
EMAIL_FROM_BOOKINGS=TailoraHub Bookings <bookings@tailorahub.com>
EMAIL_FROM_SUPPORT=TailoraHub Support <support@tailorahub.com>
EMAIL_FROM_PAYMENTS=TailoraHub Payments <payments@tailorahub.com>
EMAIL_FROM_ADMIN=TailoraHub Admin <admin@tailorahub.com>
```

Your provider must authorize each `From` alias (or use the account address as
all senders). Until SMTP is enabled, the app remains in mock mode and writes
messages to the configured outbox instead of sending them.

For Amazon SES or SendGrid, set `EMAIL_PROVIDER` and its provider secret, then
verify the domain/aliases with that provider before switching production traffic.

## EC2 runtime secret loading

The backend can load the JSON application secret at startup using the EC2
instance role. Set only the secret identifier in the container environment:

```dotenv
AWS_SECRETS_MANAGER_SECRET_ID=arn:aws:secretsmanager:eu-north-1:<account>:secret:tailorahub/production/application-<suffix>
AWS_SECRETS_MANAGER_REGION=eu-north-1
```

The application reads the secret in memory and does not write its values to a
file or log them. Remove the old plaintext `DATABASE_URL`, JWT, admin, and
Aadhaar variables from the container after enabling this setting.
