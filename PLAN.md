# Family Keeper — Implementation Plan

## Context

Family Keeper is a family management PWA — shared lists (grocery, todo, chores), Google Calendar integration, AI image-to-list. Domain: **familykeeper.app**.

**Architecture:** Monorepo with two independently deployable apps — Next.js frontend (Vercel) and FastAPI backend (Railway), with PostgreSQL + Redis for data, Cloudflare R2 for file storage.

---

## Completed Phases

### Phase 1 — Infrastructure & Scaffolding ✓
Monorepo (pnpm + Turborepo), Docker Compose (Postgres 16 + Redis 7), FastAPI skeleton, Next.js 15 + React 19 + Tailwind v4, CI pipeline, health check.

### Phase 2 — Authentication & User Model ✓
JWT auth (access 15min + refresh 30d), bcrypt (cost 12), Redis blacklist, rate limiting (10/min/IP), register/login/refresh/logout endpoints, Zustand auth store, protected routes. Google OAuth sign-in (openid email profile scope, auto-link by email, password-less accounts for Google-only users). Landing page with conditional Dashboard/Sign-in links.

### Phase 3 — Family Core ✓
Families, members, roles (parent/child, renameable), invite codes (8-char, time/use-limited), RBAC via FastAPI dependencies, family CRUD, member management, bottom nav.

### Phase 4 — Lists & Tasks ✓
List CRUD (todo/grocery/chores/custom), items with bulk add, reorder (gapped integers), photo enforcement, R2 pre-signed URL uploads, PhotoUpload component, 5s polling.

### Phase 5 — AI Image-to-List & Google Calendar ✓
Claude Vision API for image-to-list (with Pillow compression), Google Calendar OAuth2 (Fernet-encrypted tokens, parallel event fetch, Redis cache), FullCalendar frontend. 97 backend tests passing.

### Phase 6 — PWA ✓
Serwist service worker (NetworkOnly auth, NetworkFirst API, CacheFirst images, StaleWhileRevalidate static), InstallPrompt (Android + iOS), PWA manifest with full icon set.

### Phase 7 — Hardening & Deployment ✓
Sentry (backend + frontend, gated on DSN), security middleware (X-Content-Type-Options, X-Frame-Options, HSTS, Referrer-Policy, X-Request-ID), vercel.json (security headers + CSP), railway.toml (health check, release command), deploy.yml (CI gate).

### Phase 8 — Offline Banner & SSE Real-Time ✓
OfflineBanner component, Redis Pub/Sub (`publish_list_event` + `subscribe_list`), SSE endpoint with token auth + 30s heartbeat, `useListSSE` hook with exponential backoff, 5s polling fallback, SW `NetworkOnly` for `/stream`.

### Phase 8.5 — Push Notifications ✓
VAPID key pair (env vars), `push_subscriptions` table, `pywebpush` + `PushService` (subscribe, send_to_user/family, 410 cleanup), API endpoints (vapid-key, subscribe, unsubscribe), triggers on item assignment/completion/grocery adds (fire-and-forget), `usePushNotifications` hook, `PushPermissionBanner`, SW push + notificationclick handlers. 109 backend tests.

---

## Remaining Phases

### Phase 9 — E2E Playwright Tests (in progress)

**Goal:** Full-stack E2E coverage exercising browser → Next.js → FastAPI → DB.

Playwright config (`webServer` auto-starts backend + frontend), API-based test data seeding, 23 E2E tests across 5 spec files:
- `auth.spec.ts` (5) — register, login, wrong password, logout, unauth redirect
- `family.spec.ts` (5) — create, invite code, join, members, update name
- `lists.spec.ts` (6) — create grocery, add item, multiple items, mark done, delete, chore+photo
- `items-workflow.spec.ts` (4) — full flow, item count, undo, seeded items
- `navigation.spec.ts` (3) — bottom nav, breadcrumbs, deep links

CI: `e2e` job in `.github/workflows/ci.yml` (Postgres + Redis services, build + test).

**Remaining Phase 9 work:**
- Backend unit test coverage improvements (target 90%)
- Frontend unit/integration tests (stores, hooks, components)
- CI enhancements (`pip audit`, `pnpm audit`, coverage thresholds)
- Go-forward strategy & monitoring

---

## Key Technology Decisions

| Decision | Choice | Why |
|---|---|---|
| Monorepo | pnpm + Turborepo | Caching, polyglot, simple config |
| Backend | FastAPI + SQLAlchemy 2.0 async | Async-native, Pydantic v2 integration |
| Auth | JWT access (15min) + rotated refresh (30d) | Stateless access, revocable refresh |
| File storage | Cloudflare R2 (pre-signed URLs) | Zero egress, S3-compatible |
| AI OCR | Claude Vision (claude-sonnet-4-6) | Best handwriting recognition |
| Calendar | Google Calendar read-only OAuth2 | User requirement, minimal scope |
| PWA | Serwist (next-pwa successor) | Active maintenance, Next.js 15 support |
| Observability | Sentry | Industry standard, free tier |
| Deployment | Vercel (frontend) + Railway (backend) | Auto-deploy from main, zero config |
