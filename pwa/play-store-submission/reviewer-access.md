# Reviewer Access Instructions

Google Play reviewers need a way to access the app without depending on personal OTP delivery.

## App URL

Website/PWA: https://tailorahub.com

Android package currently configured in the TWA project: com.tailorahub.twa

## Test Credentials

Use the Password login tab. OTP login is available for real users, but reviewers should use password login for reliable testing.

### Customer Demo Login

Role: Customer

Identifier: create-demo-customer@tailorahub.com or a dedicated demo phone number

Password: Customer@12345

Status needed: Active customer account with at least one completed order and one in-progress order if possible.

### Tailor Demo Login

Role: Tailor

Identifier: anika_demo or anika.tailor@tailorahub.com

Password: Tailor@12345

Status needed: Active and approved tailor account. The backend seeds demo tailors when demo seeding is enabled.

Backup tailor:

Identifier: velstitch_demo or velstitch.tailor@tailorahub.com

Password: Tailor@12345

### Admin Demo Login

Role: Admin

Identifier: admin

Password: Admin@12345

Use this only if Google asks for admin access because admin features are inside the same app.

## Reviewer Notes

- The first screen lets reviewers choose Customer, Tailor or Admin.
- Location permission can be allowed to test nearby tailor search and booking location picker.
- Razorpay is configured for payment processing. Use Razorpay test mode credentials and test payment methods during review until production payments are approved.
- Delivery completion uses OTP after payment is complete.
- Account deletion request is available from the Support section.

## Before Submission Checklist

- Confirm the customer demo account exists in the production database.
- Confirm the tailor demo account is approved and visible to customers.
- Confirm admin password is exactly the configured production admin password.
- Confirm OTP is not required for reviewer demo password login.
- Confirm no private real customer/tailor data is shown in the demo flow.
