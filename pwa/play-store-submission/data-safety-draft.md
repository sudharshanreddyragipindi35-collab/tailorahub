# Play Console Data Safety Draft

Use this as a guide while filling the Google Play Data Safety form. Adjust it if your live implementation changes.

## Data Collection

Does the app collect or share user data? Yes.

Is all user data encrypted in transit? Yes, app traffic uses HTTPS.

Can users request data deletion? Yes, through the in-app Support account deletion request and the privacy policy contact email.

## Data Types Collected

### Personal Info

Collected: Name, email address, phone number, user/customer/tailor identifiers.

Purpose: Account creation, login, booking, support, notifications and fraud prevention.

### Location

Collected: Approximate and precise location when users allow location permission or confirm a booking/tailor location.

Purpose: Nearby tailor search, tailor profile location, customer measurement location and booking fulfillment.

### Photos and Videos

Collected: Tailor profile media, offers media, stitched item/dispute images where uploaded.

Purpose: Tailor profile display, offers, service proof, disputes and support.

### Financial Info

Collected: Payment status, order amount, tax/fee breakdown, Razorpay payment/order identifiers, wallet ledger, withdrawal request details.

Purpose: Payment processing, wallet accounting, order confirmation, refunds or withdrawal workflow.

Important: Raw card, UPI PIN, bank login or sensitive payment credentials are handled by Razorpay and not stored directly by TailoraHub.

### App Activity

Collected: Bookings, orders, favorites, following, feedback, support tickets, search/filter activity and status changes.

Purpose: Core app functionality, order management, support and improvement.

### Device or Other IDs

Collected: Basic browser/device/session identifiers may be used for authentication, security and troubleshooting.

Purpose: Account security, session management and diagnostics.

## Data Sharing

Data may be shared with:

- Razorpay for payment processing.
- Google Maps for maps, geocoding and location picker features.
- AWS or hosting/storage providers for app hosting, database, media and logs.
- Selected tailors/customers for order fulfillment.
- Admin/support users for dispute, payment and account operations.
- Legal authorities if required by law.

TailoraHub does not sell personal data.

## Security Practices

- HTTPS for web and API traffic.
- Password hashing.
- OTP expiry and purpose separation.
- Role-based access for customer, tailor and admin functions.
- Customer-facing APIs should not expose tailor UPI/bank details.
- Delivery OTP should be generated only after payment is completed.

## App Audience

Intended audience: Adults and general users looking for tailoring services. Not primarily directed to children.

Children under 13: No.
