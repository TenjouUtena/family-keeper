# Privacy Policy

**Last updated:** March 20, 2026

Family Keeper ("we", "us", "our") operates the Family Keeper application at **familykeeper.app**. This Privacy Policy explains what data we collect, how we use it, and your rights regarding that data.

## 1. Data We Collect

### 1.1 Account Information

When you create an account, we collect:

- **Email address** — Used for account identification and login.
- **Username** — Used for display within your family groups.
- **Password** — Stored as a bcrypt hash. We never store or have access to your plaintext password.
- **Avatar URL** — Optional profile picture URL.

If you sign in with Google, we also receive your Google subject ID, email, and profile information from Google's OAuth service.

### 1.2 Family & List Data

When you use the app, we store:

- **Family groups** you create or join, including membership roles (e.g., Parent, Child).
- **Lists and items** you create (todos, groceries, chores, custom lists), including item content, notes, status, due dates, and assignment information.
- **Invite codes** you generate, including creation time and usage limits.

### 1.3 Photos & Attachments

- **Task photos** (e.g., chore completion photos) are uploaded to Cloudflare R2 object storage. We store the file, its metadata (filename, MIME type, size), and which user uploaded it.
- **AI image-to-list photos** are sent to the Anthropic Claude API for text extraction. These images are processed in real time and are not stored by us beyond the duration of the API request. Refer to [Anthropic's usage policy](https://www.anthropic.com/policies) for how they handle data sent to their API.

### 1.4 Google Calendar Data

If you connect your Google Calendar:

- We store your OAuth access and refresh tokens, **encrypted at rest** using Fernet symmetric encryption.
- We read your calendar names and events to display them within the app. We do **not** modify, create, or delete any calendar data in your Google account.
- You can disconnect your Google Calendar at any time, which immediately deletes your stored credentials.

### 1.5 Push Notification Data

If you enable push notifications, we store:

- Your device's push subscription endpoint URL.
- Encryption keys (p256dh and auth) required to send notifications to your device.

You can unsubscribe at any time, which deletes this data.

### 1.6 Technical & Usage Data

- **Error tracking:** We use Sentry to capture application errors and performance data. This may include browser type, operating system, and anonymized interaction traces.
- **Analytics:** We use Vercel Analytics and Speed Insights to understand general usage patterns. This data is aggregated and does not include personal content.
- **Server logs:** API requests generate logs that may include IP addresses, request paths, and request IDs. These are used for debugging and security monitoring.

### 1.7 Cookies & Local Storage

- **Authentication tokens** are stored in browser cookies and local storage to maintain your session.
- **Service Worker caches** store app assets and API responses locally on your device for offline access.
- We do not use third-party advertising or tracking cookies.

## 2. How We Use Your Data

We use your data to:

- **Provide the service** — Store and display your lists, tasks, calendars, and family information.
- **Authenticate you** — Verify your identity and manage sessions.
- **Send notifications** — Notify you of task assignments, completions, and other family activity (when enabled).
- **Process images** — Extract text from photos you upload using AI (Anthropic Claude API).
- **Improve the app** — Monitor errors, performance, and general usage patterns.
- **Enforce security** — Rate-limit requests, detect abuse, and protect accounts.

We do **not**:

- Sell your data to third parties.
- Use your data for advertising.
- Share your family's content with other families or users outside your family group.

## 3. Data Sharing

We share data only with the following service providers, strictly to operate the app:

| Provider | Purpose | Data Shared |
| --- | --- | --- |
| **Cloudflare (R2)** | File storage | Uploaded photos and attachments |
| **Anthropic (Claude API)** | AI text extraction | Photos submitted for image-to-list |
| **Google (OAuth & Calendar API)** | Calendar integration | OAuth tokens, calendar event reads |
| **Sentry** | Error tracking | Error reports, performance traces |
| **Vercel** | Frontend hosting & analytics | Aggregated usage data |
| **Railway** | Backend hosting | Application data in transit |

We do not share your data with any other third parties unless required by law.

## 4. Data Security

We implement the following measures to protect your data:

- All data in transit is encrypted via HTTPS/TLS.
- Passwords are hashed with bcrypt (cost factor 12).
- Google OAuth tokens are encrypted at rest with Fernet encryption.
- Refresh tokens are stored as SHA-256 hashes, never in plaintext.
- Database access is restricted to authenticated backend services only.
- Pre-signed URLs for file access expire after a short time window.

For full details, see our [Security Policy](SECURITY.md).

## 5. Data Retention

- **Account data** is retained as long as your account is active.
- **List and task data** is retained as long as the associated family exists.
- **Authentication tokens** expire automatically (access tokens after 15 minutes, refresh tokens after 30 days).
- **Blacklisted tokens** are automatically purged from Redis upon expiration.
- **Push subscriptions** are removed when you unsubscribe or if delivery fails.

If you delete your account, your personal data will be removed. Shared family data (lists, items) that you contributed to may remain accessible to other family members.

## 6. Your Rights

You have the right to:

- **Access** your personal data stored in the app.
- **Correct** inaccurate data by updating your profile.
- **Delete** your account and associated personal data.
- **Disconnect** third-party integrations (Google Calendar) at any time, immediately removing stored credentials.
- **Withdraw consent** for push notifications at any time.
- **Export** your data by contacting us.

To exercise any of these rights, contact us at **privacy@familykeeper.app**.

## 7. Children's Privacy

Family Keeper is designed for family use, including children as family members. However:

- Account creation requires a valid email address.
- Children's accounts are expected to be set up and supervised by a parent or guardian.
- We do not knowingly collect data from children under 13 without parental consent. If you believe a child has provided us personal data without consent, please contact us and we will promptly delete it.

## 8. Changes to This Policy

We may update this Privacy Policy from time to time. Changes will be posted in this document with an updated "Last updated" date. Continued use of the app after changes constitutes acceptance of the updated policy.

## 9. Contact Us

If you have questions about this Privacy Policy or our data practices:

- **Privacy inquiries:** privacy@familykeeper.app
- **Security issues:** security@familykeeper.app
