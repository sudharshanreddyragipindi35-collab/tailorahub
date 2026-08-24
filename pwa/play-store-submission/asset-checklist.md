# Play Store Asset Checklist

## Existing Assets Found

App icon 512 x 512:

- frontend/public/icons/icon-512.png
- pwa/android-twa/store_icon.png

Maskable icon 512 x 512:

- frontend/public/icons/maskable-512.png

Existing reference screenshots:

- frontend/src/assets/tailorahub-mobile-home-reference.png, 941 x 1672
- frontend/src/assets/tailorahub-home-reference.png, 1672 x 941

## Assets Still Needed for Play Store Listing

### Feature Graphic

Ready file:

- pwa/play-store-submission/assets/feature-graphic-1024x500.png

Size: 1024 x 500 px

Visual: dark luxury TailoraHub background with gold brand accent, tailoring mannequin imagery and marketplace/payment message.

### Phone Screenshots

Minimum: at least 2 screenshots.

Recommended: 4 to 6 screenshots for a stronger listing.

Suggested screenshots:

1. Customer nearby tailor search and cards.
2. Customer order tracking / in-progress orders.
3. Tailor dashboard orders or availability.
4. Tailor services/pricing or wallet.
5. Admin finance or approvals screen, only if you want to show admin value.

Screenshot safety:

- Use demo accounts only.
- Do not show real customer phone numbers, real email addresses, payment keys, bank details or private addresses.
- Use portrait phone screenshots where possible.

## TWA / Asset Links Check

Current TWA package in pwa/android-twa/twa-manifest.json:

- com.tailorahub.twa

Current assetlinks package in frontend/public/assetlinks.json:

- com.tailorahub.twa

Before uploading to Play Store, keep these exactly the same:

- Android applicationId / package name
- assetlinks.json package_name
- signing certificate SHA-256 fingerprint

Current assetlinks URL should work:

- https://tailorahub.com/.well-known/assetlinks.json

## Store Text Files

Use these prepared files:

- pwa/play-store-submission/play-store-listing.md
- pwa/play-store-submission/privacy-policy.md
- pwa/play-store-submission/reviewer-access.md
- pwa/play-store-submission/data-safety-draft.md
- pwa/play-store-submission/release-notes.md


