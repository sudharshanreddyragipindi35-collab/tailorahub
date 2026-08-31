# Security policy

## Reporting a vulnerability

Do not open a public issue containing a vulnerability, credential, personal record, payment reference, OTP, Aadhaar value, exploit, or production URL that should remain private.

Send the report through the repository's private vulnerability-reporting channel or the private security contact configured for the production organization. Include the affected role and route, impact, safe reproduction steps, and a request ID when available. Use synthetic accounts and redacted evidence only.

The production owner must acknowledge a credible report, restrict disclosure to the response team, preserve relevant audit evidence, rotate or revoke exposed credentials, and deploy a verified fix before public disclosure. Exact response-time commitments and the permanent security mailbox remain Phase 9 production-account items.

## Supported version

Security fixes apply to the currently deployed immutable production commit. Old containers and frontend builds are unsupported after a replacement is verified and rolled out.

## Repository rules

- Store production secrets in AWS Secrets Manager and inject them into ECS at runtime.
- Never use `VITE_` for a server secret; every `VITE_` value is public browser code.
- Never commit `.env`, credential files, signing keys, identity documents, database dumps, production screenshots, or deployment archives.
- Rotate a secret immediately if it appears in source, Git history, logs, screenshots, ZIP files, support tickets, or a container layer.
- Require the security workflow to pass before merging a production release.
