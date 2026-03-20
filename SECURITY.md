# Security Policy

**Last updated:** March 20, 2026

Family Keeper takes the security of our platform and your family's data seriously. This document outlines our security practices and how to report vulnerabilities.

## Supported Versions

| Version | Supported |
| ------- | --------- |
| Latest (production) | Yes |
| Older versions | No |

Only the latest production deployment receives security updates.

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly. **Do not open a public GitHub issue.**

- **Email:** security@familykeeper.app
- **Response time:** We aim to acknowledge reports within 48 hours and provide a detailed response within 5 business days.
- **Disclosure:** We request that you give us reasonable time to address the issue before any public disclosure.

Please include:

1. A description of the vulnerability and its potential impact
2. Steps to reproduce the issue
3. Any relevant screenshots or proof-of-concept code
4. Your contact information for follow-up

## Security Architecture

### Authentication

- **JWT access tokens** with short-lived expiry (15 minutes) to limit the window of compromise.
- **Refresh tokens** are hashed (SHA-256) before storage — plaintext tokens are never persisted.
- **Token rotation** is enforced on refresh; old tokens are revoked immediately.
- **Password hashing** uses bcrypt with a cost factor of 12.
- **Google OAuth 2.0** integration uses the authorization code flow with state parameter validation to prevent CSRF.
- **Token blacklisting** via Redis ensures revoked tokens cannot be reused during their remaining lifetime.

### Authorization

- All data is scoped to families. Users can only access resources belonging to families they are members of.
- Role-based access control (Parent/Child roles) restricts sensitive operations such as family settings and member management.
- API endpoints enforce family membership checks via server-side middleware.

### Data Protection

- **In transit:** All traffic is served over HTTPS with HSTS enabled (max-age 63072000 seconds, including subdomains, with preload).
- **At rest:** Google OAuth credentials (access and refresh tokens) are encrypted using Fernet symmetric encryption before database storage.
- **Database queries** use parameterized statements via SQLAlchemy to prevent SQL injection.
- **File uploads** are validated server-side for MIME type (images only) and size (10 MB maximum).

### Rate Limiting

- Authentication endpoints: 10 requests per minute per IP address.
- AI image-to-list: 10 requests per hour per family.
- Rate limiting uses Redis sorted sets with sliding window expiration.

### HTTP Security Headers

The following headers are enforced on all responses:

- `Content-Security-Policy` — Restricts resource loading to trusted origins.
- `X-Content-Type-Options: nosniff` — Prevents MIME-type sniffing.
- `X-Frame-Options: DENY` — Prevents clickjacking via iframe embedding.
- `Referrer-Policy: strict-origin-when-cross-origin` — Limits referrer information leakage.
- `Permissions-Policy` — Restricts browser feature access (e.g., camera limited to same-site).

### CORS

Cross-origin requests are restricted to `familykeeper.app` domains only.

### File Storage

- Uploaded files are stored in Cloudflare R2 (S3-compatible object storage).
- Access is controlled via pre-signed URLs with time-limited expiration (10 minutes for uploads, 1 hour for downloads).
- Files are organized in a family/list/item hierarchy to enforce logical separation.

### Service Worker

- Authentication endpoints use a `NetworkOnly` strategy to prevent token caching.
- API calls use `NetworkFirst` to ensure fresh data while supporting offline fallback.
- Cached images expire after 7 days.

### Infrastructure

- **Frontend** is deployed on Vercel with automatic HTTPS and edge caching.
- **Backend** is deployed on Railway with health-check monitoring.
- **Database** is PostgreSQL 16 with connection-level access controls.
- **Cache/Pub-Sub** uses Redis 7 with authentication.

### CI/CD Security

- GitHub Actions runs lint, type-check, unit test, and E2E test pipelines on every change.
- Dependency audits are performed as part of the CI pipeline.
- Secrets are managed via environment variables and are never committed to source control.

## Best Practices for Users

- Use a strong, unique password for your Family Keeper account.
- Do not share your invite codes publicly — they grant access to your family's data.
- If you suspect unauthorized access, change your password and revoke all sessions by logging out.
- Keep your browser up to date to benefit from the latest security protections.
