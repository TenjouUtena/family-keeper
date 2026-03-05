# Family Keeper — Implementation Plan

## Context

Family Keeper is a family management PWA — shared lists (grocery, todo, chores), Google Calendar integration, AI image-to-list. Domain: **familykeeper.app**.

**Architecture:** Monorepo with two independently deployable apps — Next.js frontend (Vercel) and FastAPI backend (Railway), with PostgreSQL + Redis for data, Cloudflare R2 for file storage.

---

## Completed Phases

### Phase 1 — Infrastructure & Scaffolding ✓
Monorepo (pnpm + Turborepo), Docker Compose (Postgres 16 + Redis 7), FastAPI skeleton, Next.js 15 + React 19 + Tailwind v4, CI pipeline, health check.

### Phase 2 — Authentication & User Model ✓
JWT auth (access 15min + refresh 30d), bcrypt (cost 12), Redis blacklist, rate limiting (10/min/IP), register/login/refresh/logout endpoints, Zustand auth store, protected routes.

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

---

## Remaining Phases

### Phase 8 — Offline Banner & SSE Real-Time ✓

**Goal:** Replace 5s polling with real-time SSE updates, add offline awareness.

1. **Offline banner** — `OfflineBanner` component (sticky amber bar when `navigator.onLine = false`)
2. **Redis Pub/Sub helper** — `pubsub.py` with `publish_list_event` (fire-and-forget on shared connection) and `subscribe_list` (dedicated connection per SSE client)
3. **Event publishing** — All list mutations (add/update/delete/reorder items, update list) publish events after commit
4. **SSE endpoint** — `GET /v1/families/{familyId}/lists/{listId}/stream?token=...` with token-based auth (EventSource can't send headers), 30s heartbeat, Redis subscription cleanup on disconnect
5. **Frontend SSE hook** — `useListSSE` with EventSource, exponential backoff (max 5 retries), invalidates React Query cache on events
6. **Polling fallback** — `useListDetail` accepts optional `refetchInterval`; polls at 5s only when SSE is disconnected
7. **Service worker exclusion** — `NetworkOnly` rule for `/stream` paths before API cache rule

---

### Phase 8.5 — Push Notifications (pending)

**Goal:** Native push notifications for key family events.

1. **VAPID key pair** — generate and store as env vars (`VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_MAILTO`)
2. **Database** — `push_subscriptions` table + Alembic migration (user_id, endpoint, p256dh, auth, created_at)
3. **Backend** — `pywebpush` library, notification service
4. **API endpoints**
   - `POST /v1/push/subscribe` — register push subscription
   - `DELETE /v1/push/subscribe` — unregister
   - `GET /v1/push/vapid-key` — public VAPID key for frontend
5. **Triggers** — chore assigned to child, chore completed (notify parent), new grocery item added
6. **Frontend** — permission request flow, subscription registration, SW push event handler
7. **iOS considerations** — iOS 16.4+ supports Web Push in PWA mode

### Phase 9 — Comprehensive Testing & Go-Forward

**Goal:** Production confidence with high test coverage and a go-forward strategy.

1. **Backend test suite** — target 90% coverage
   - Unit: security, permissions, invite codes, AI service, calendar service
   - Integration: full auth → family → list → AI flows
2. **Frontend test suite**
   - Unit: stores, utils, hooks
   - Integration: component flows (login, list management, AI capture)
3. **E2E tests** (Playwright)
   - Auth flow, family creation/join, list CRUD, calendar
   - Mobile Chrome + Mobile Safari projects
4. **CI enhancements**
   - `pip audit` + `pnpm audit` in CI
   - Coverage thresholds enforced
5. **Go-forward strategy** — feature roadmap, monitoring dashboards

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
