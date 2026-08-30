# TailoraHub private administrator deployment

## Result

- Public users enter through `https://tailorahub.com/` and can choose only Customer or Tailor.
- Administrators enter through `https://tailorahub.com/admin`.
- The admin page is marked `noindex` and is excluded from the PWA service-worker cache.
- The backend still requires a valid administrator token for every admin operation.
- `ADMIN_ALLOWED_NETWORKS` rejects admin login and admin API traffic outside the approved network when configured.

`/admin` is a path on the existing domain, not a separate domain. Privacy comes from the IP rules below, not from the URL being unknown.

## Important IP rule

Do not enter the computer's private LAN address (`127.0.0.1`, `192.168.x.x`, or `10.x.x.x`) in AWS WAF. AWS sees the public egress IP of the internet connection or VPN. For reliable access, use one of:

1. A static office/home public IP.
2. A VPN with one fixed egress IP.
3. AWS Client VPN, with its fixed outbound network allowed.

If a normal ISP changes the public IP, the admin portal will become unavailable until the allowlist is updated.

## 1. Configure the backend container

Set these environment variables on the production backend container:

```env
ADMIN_ALLOWED_NETWORKS=YOUR_PUBLIC_IP/32
ADMIN_TRUSTED_PROXY_NETWORKS=127.0.0.1/32,::1/128,YOUR_NGINX_OR_DOCKER_PROXY_CIDR
```

Example:

```env
ADMIN_ALLOWED_NETWORKS=203.0.113.25/32,2001:db8::25/128
ADMIN_TRUSTED_PROXY_NETWORKS=127.0.0.1/32,::1/128,172.16.0.0/12
```

Use an exact IPv4 `/32` or IPv6 `/128` for each approved administrator connection. Mobile carrier addresses can change, so re-verify a mobile address after a network reconnect or use a fixed-egress VPN for reliable access. Use the narrowest real proxy network possible instead of the broad Docker example. Restart the backend container after changing the environment. An empty `ADMIN_ALLOWED_NETWORKS` disables the application-level IP check, so do not leave it empty in production.

The following backend paths are protected by this setting:

- `/api/auth/admin/login`
- `/api/admin/*`
- `/api/v1/admin/*`

The normal `/api/auth/login` endpoint no longer accepts the Admin role.

## 2. Protect `/admin` with AWS WAF

In AWS Amplify, attach an AWS WAF web ACL to the TailoraHub app. The web ACL scope must be **CloudFront (Global)**.

Create separate IPv4 and IPv6 IP sets containing only the approved exact addresses. Then configure these rules in order:

1. **AllowApprovedAdminIPs**
   - URI path matches `/admin` or a child path (apply URL decode and lowercase text transformations).
   - Source address is in the approved IPv4 **or** IPv6 IP set.
   - Action: **Allow**.
2. **BlockOtherAdminIPs**
   - URI path matches `/admin` or a child path.
   - Action: **Block**.

Keep the web ACL default action as Allow so the customer and tailor site remains public. Enable WAF logging before launch and test from both the approved network and a mobile-data connection.

AWS references:

- [Enable AWS WAF for an Amplify application](https://docs.aws.amazon.com/amplify/latest/userguide/getting-started-using-waf.html)
- [Amplify firewall and IP-set support](https://docs.aws.amazon.com/amplify/latest/userguide/WAF-integration.html)

## 3. Keep the SPA rewrite

Amplify must rewrite application routes to `index.html` so `/admin` loads the React entry:

```json
[
  {
    "source": "</^[^.]+$|\\.(?!(css|gif|ico|jpg|jpeg|js|png|txt|svg|woff|woff2|ttf|map|json|webmanifest)$)([^.]+$)/>",
    "target": "/index.html",
    "status": "200"
  }
]
```

The WAF check occurs before this application rewrite.

## 4. Verification before going live

Run all four checks:

1. Open `https://tailorahub.com/` and confirm Admin is not displayed.
2. From an unapproved connection, open `https://tailorahub.com/admin`; expect an AWS 403 response.
3. From the approved connection, open `/admin`, sign in, and load Dashboard, Customers, Tailors, Orders, Payments, Support, and Audit.
4. From an unapproved connection, call an admin API; expect HTTP 403 even with a valid token.

Do not treat the URL, `noindex`, or frontend role hiding as security controls. Keep WAF, backend IP restriction, administrator authentication, strong credentials, and audit logging enabled together.
