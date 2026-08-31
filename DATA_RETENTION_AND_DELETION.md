# TailoraHub data retention and account deletion procedure

## Request and approval path

Customers and tailors request account deletion through the existing support-ticket category. The product intentionally does not expose an immediate destructive button. An authorized administrator verifies the requester, checks the account identifier, and records the request in the private support system.

Deletion is blocked while an order is active or a payment is pending. The support owner first resolves or cancels open work using the normal business process. This prevents loss of delivery, payment, refund, or dispute evidence.

## Deletion result

After the safety check passes, the administrator deletion endpoint:

- immediately revokes active refresh sessions and disables login;
- cancels open booking requests;
- removes profile and portfolio media through the configured storage service;
- clears phone, email, address, coordinates, profile image, password hash, Aadhaar hash/encrypted value, date of birth, username, and referral code;
- replaces display identity with a non-identifying deleted-account label; and
- keeps only pseudonymized transaction relationships needed for order, payment, refund, dispute, fraud, audit, and financial reconciliation.

The audit event records that anonymization occurred but does not copy the person's previous name or identity fields into the deletion event.

## Operational retention classes

| Data class | Source behaviour | Production decision still required |
|---|---|---|
| OTP records | Expired records are removed by the scheduler | Confirm the cleanup job and alarm in production |
| Refresh sessions | Expired sessions and revoked sessions older than seven days are removed | Confirm scheduler execution in production |
| Customer/tailor profile PII | Anonymized after an approved safe deletion | Verify representative deletion and S3 object removal |
| Orders, payments, refunds, disputes, wallet and audit records | Retained with pseudonymized account references | Legal/finance owner must approve the exact retention period |
| Support tickets and operational logs | Access-controlled; request bodies, headers and query strings are excluded from application logs | Approve retention periods and verify CloudWatch lifecycle policies |
| Backups | Managed through encrypted production backup policy | Approve backup retention and test expiry/restore handling for deleted identities |

The legal, tax, payment-provider, KYC-provider, and privacy owners must approve exact periods before launch. Do not shorten a required financial retention period or promise immediate erasure from immutable backups without that review.

## Verification record

For each production deletion test, record the support ticket, approver, timestamp, safety-check result, anonymized database result, session revocation, media-object deletion, audit event, and any retained statutory record class. Use identifiers only in the private operations system.
