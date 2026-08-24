# TailoraHub Play Store Security Checklist

## Automated Checks Already Covered

- Android package is generated as a Trusted Web Activity wrapper.
- App uses HTTPS domain hosting.
- Digital Asset Links are published for the configured Android package.
- App icon and maskable icon are available.
- Backend health endpoint is available through HTTPS.

## Required Production Configuration

- Keep all API keys in environment variables only.
- Do not commit Razorpay key secret, SMTP password, AWS keys, Google Maps key or database password.
- Razorpay live mode should only be enabled after business/KYC approval and production testing.
- Google Maps API key should be restricted by website referrers and only required Maps APIs.
- JWT secrets must be stable and strong in production.
- CORS must allow only production frontend domains and local development domains.
- Admin password should be set explicitly in backend/.env and rotated if shared.

## Manual Checks Before Play Store Submission

- Login works for reviewer customer, tailor and admin accounts.
- Customer booking works with demo data.
- Razorpay test payment opens and returns payment status correctly.
- Tailor wallet is credited with net amount after commission only after payment verification.
- Withdrawal request does not auto-pay without admin approval.
- Delivery OTP is unavailable until payment is completed.
- Completed orders hide tailor update/OTP controls and show customer feedback option.
- Account deletion request is available from Support.
- Privacy policy page is public at https://tailorahub.com/privacy.
- Screenshots do not expose real personal data or secrets.
