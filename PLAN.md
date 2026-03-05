# Family Keeper — Phased Implementation Plan

## Context

Family Keeper is a greenfield family management app. The project currently contains only `DESIGN.md`. This plan covers everything needed to go from empty repo to production-ready app: infrastructure, auth, core features, integrations, and polish.

**Architecture:** Monorepo with two independently deployable apps — Next.js frontend (Vercel) and FastAPI backend (Railway), with PostgreSQL + Redis for data.

---

## Monorepo Structure

```
family-keeper/
├── apps/
│   ├── web/              # Next.js + TypeScript (Vercel)
│   └── api/              # FastAPI + Python (Railway)
├── packages/
│   └── shared-types/     # Shared TypeScript types/Zod schemas
├── docker-compose.yml    # Local dev: Postgres + Redis
├── pnpm-workspace.yaml
├── turbo.json
└── .github/workflows/    # CI/CD
```

---

## Phase 1 — Infrastructure & Scaffolding

**Goal:** Clone → one command → full local stack running. No features, just the skeleton.

### Deliverables

1. **Monorepo setup** — `pnpm-workspace.yaml`, `turbo.json`, root `package.json` with `dev`/`build`/`test`/`lint` scripts
2. **Docker Compose** — Postgres 16 (port 5432) + Redis 7 (port 6379) for local dev only
3. **Backend skeleton** (`apps/api/`)
   - `pyproject.toml` (Poetry): fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, redis[asyncio], python-jose, passlib[bcrypt], httpx
   - `app/main.py` — FastAPI app with CORS middleware and lifespan
   - `app/config.py` — pydantic-settings `Settings` class
   - `app/database.py` — async SQLAlchemy engine + session factory
   - `app/routers/health.py` — `GET /health` → `{"status":"ok","db":bool,"redis":bool}`
   - `alembic/` configured with async support
   - `tests/conftest.py` + `tests/test_health.py`
4. **Frontend skeleton** (`apps/web/`)
   - Next.js 15 + React 19 + TypeScript + Tailwind CSS v4
   - TanStack React Query, Zustand, Zod
   - `public/manifest.json` (PWA skeleton)
   - `src/app/layout.tsx`, `src/app/page.tsx` (placeholder landing)
   - `src/lib/api-client.ts` (empty typed fetch wrapper)
   - vitest + Playwright + @testing-library/react configured
5. **CI pipeline** — `.github/workflows/ci.yml`: lint, typecheck, test (matrix: web + api)
6. **`.env.example`** — all env vars documented, no secrets committed
7. **`.gitignore`** — node_modules, .venv, __pycache__, .env, .next, dist

### End State
- `docker-compose up -d` → Postgres + Redis running
- `pnpm dev` → Next.js on :3000, FastAPI on :8000
- `GET localhost:8000/health` → 200
- `pnpm test` → green

---

## Phase 2 — Authentication & User Model

**Goal:** Users can register, log in, and receive JWTs. Secure auth foundation.

### Deliverables

1. **Database: `users` table** (UUID PK, email, username, password_hash, avatar_url, is_active, timestamps)
2. **Database: `refresh_tokens` table** (token_hash stored, never raw; expiry, revoked flag)
3. **Alembic migration** `0001_create_users.py`
4. **Auth system** (`app/core/security.py`)
   - Password hashing: bcrypt, cost factor 12
   - JWT: HS256, access token 15min, refresh token 30 days with rotation
   - Redis blacklist for logged-out access tokens (by JTI)
5. **API endpoints**
   - `POST /v1/auth/register` — create user, return tokens
   - `POST /v1/auth/login` — authenticate, return tokens
   - `POST /v1/auth/refresh` — rotate tokens
   - `POST /v1/auth/logout` — blacklist access token
   - `GET /v1/users/me` — current user profile
   - `PATCH /v1/users/me` — update profile
6. **Rate limiting** — Redis-backed sliding window on auth endpoints (10 req/min/IP)
7. **FastAPI dependency** `get_current_user` in `app/core/dependencies.py`
8. **Frontend auth pages**
   - `(auth)/login/page.tsx`, `(auth)/register/page.tsx` with centered card layout
   - `src/stores/auth-store.ts` — Zustand: access token in memory
   - `src/hooks/useAuth.ts` — login, logout, register mutations
   - `src/lib/api-client.ts` — auth headers + 401 refresh handling
   - `(app)/layout.tsx` — authenticated shell, redirects to login if no token
   - `(app)/dashboard/page.tsx` — placeholder
9. **UI primitives** — Button, Input, Card, Form components (Tailwind-based)
10. **Tests** — backend: register/login/refresh/logout/rate-limit; frontend: LoginForm, RegisterForm

### Security Decisions
- Access token in memory (Zustand), refresh token in localStorage with strict CSP
- All API routes under `/v1/` prefix
- CORS: strict allowlist, `Authorization: Bearer` header (not cookies)
- Input validation: Pydantic v2 on all inputs, email normalized to lowercase

### End State
- Full auth flow works end-to-end
- Protected routes reject unauthenticated requests
- CI green with auth tests

---

## Phase 3 — Family Core: Groups, Roles & Membership

**Goal:** Users create families, generate invite codes, and manage roles. The central data model.

### Deliverables

1. **Database: `families` table** (UUID PK, name, parent_role_name, child_role_name — both renameable)
2. **Database: `family_members` table** (family_id, user_id, role ENUM parent/child, is_admin, joined_at; UNIQUE on family+user)
3. **Database: `invite_codes` table** (code 8-char alphanumeric, family_id, expires_at, max_uses, use_count, is_active)
4. **Alembic migration** `0002_create_families.py`
5. **RBAC system** (`app/core/permissions.py`)
   - `require_family_member(role=...)` — FastAPI dependency: verifies membership + optional role check
   - `require_family_admin()` — verifies is_admin on family_member row
   - Composable, declarative — used on every family-scoped endpoint
6. **Row-Level Security** — Postgres RLS policies on family tables as defense-in-depth (set `app.current_user_id` per session)
7. **API endpoints**
   - `POST /v1/families` — create family (creator = parent + admin)
   - `GET /v1/families` — list user's families only
   - `GET /v1/families/{id}` — family detail (members only)
   - `PATCH /v1/families/{id}` — update name, role names (admin only)
   - `POST /v1/families/{id}/invites` — generate invite code (parent only)
   - `DELETE /v1/families/{id}/invites/{code}` — revoke code
   - `POST /v1/families/join` — join via invite code
   - `PATCH /v1/families/{id}/members/{userId}` — change role (admin only)
   - `DELETE /v1/families/{id}/members/{userId}` — remove member (admin only)
8. **Invite code flow** — 8-char Base32 codes, cached in Redis for fast lookup, time/use-limited
9. **Frontend pages**
   - `/families` — list user's families
   - `/families/new` — create family form
   - `/families/[familyId]` — family home screen
   - `/families/[familyId]/members` — member management (admin)
   - `/families/[familyId]/settings` — rename roles, family settings
   - `JoinFamilyForm` — enter invite code
   - `InviteCodeDisplay` — show code + Web Share API button
10. **Mobile navigation** — bottom tab bar (Home, Lists, Calendar, Family) — mirrors native app patterns
11. **`FamilyProvider` context** — tracks current family selection across the app
12. **Tests** — create/join/leave flow, RBAC enforcement, invite code expiry/limits

### End State
- Users create families, share invite codes, others join
- Role assignment and renaming works
- All family data isolated (RLS + app-level RBAC)
- Users can belong to multiple families

---

## Phase 4 — Lists, Tasks & Photo Attachments

**Goal:** Core daily-use feature — grocery lists, todo lists, chore lists with assignments and photo proof.

### Deliverables

1. **Database: `family_lists` table** (family_id, name, list_type ENUM todo/grocery/chores/custom, visible_to_role, editable_by_role, require_photo_completion, is_archived)
2. **Database: `list_items` table** (list_id, content, notes, status ENUM pending/in_progress/done, position INT, assigned_to, due_date, completed_at, completed_by)
3. **Database: `item_attachments` table** (item_id, storage_key, filename, mime_type, file_size_bytes, is_completion_photo)
4. **Alembic migration** `0003_create_lists.py`
5. **File storage** — Cloudflare R2 (S3-compatible, zero egress fees)
   - Pre-signed upload URLs: client uploads directly to R2, never through API server
   - Flow: request upload URL → PUT to R2 → confirm upload → metadata stored
   - Image-only (JPEG, PNG, WebP, HEIC), 10MB limit, MIME verified server-side
6. **API endpoints**
   - `POST /v1/families/{id}/lists` — create list (parent-only for chore lists)
   - `GET /v1/families/{id}/lists` — list all lists (filtered by role permissions)
   - `GET /v1/lists/{id}` — list detail with items
   - `PATCH /v1/lists/{id}` — update list settings
   - `POST /v1/lists/{id}/items` — add item(s) (bulk support)
   - `PATCH /v1/lists/{id}/items/{itemId}` — update item (content, status, assignment)
   - `PATCH /v1/lists/{id}/items/reorder` — batch reorder
   - `DELETE /v1/lists/{id}/items/{itemId}` — remove item
   - `POST /v1/lists/{id}/items/{itemId}/attachments/upload-url` — get pre-signed URL
   - `POST /v1/lists/{id}/items/{itemId}/attachments/{attId}/confirm` — confirm upload
7. **Chore photo enforcement** — when `require_photo_completion = true`, API rejects status=done unless a completion photo exists uploaded by the completing user
8. **Item reordering** — gapped integer positions (0, 100, 200...), batch update on drag
9. **Frontend pages**
   - `/families/[familyId]/lists` — list of lists
   - `/families/[familyId]/lists/new` — create list form
   - `/families/[familyId]/lists/[listId]` — list detail with items
   - `ListItemRow` — checkbox, content, assigned avatar, large tap targets
   - `ItemDetail` — drawer/modal for notes, assignment, due date
   - `AttachmentUpload` — camera/file picker + upload progress
   - `DraggableList` — drag-to-reorder with mobile touch events
10. **Real-time (v1)** — TanStack Query polling every 5 seconds (upgraded to SSE in Phase 6)
11. **Tests** — CRUD flows, permission checks, photo requirement enforcement, reordering

### End State
- Parents create lists (grocery, todo, chores), set permissions
- All members add/complete items (subject to permissions)
- Chores assigned to specific members; photo proof required when configured
- Photos upload directly to R2 with progress indicator
- Mobile-optimized: large tap targets, swipe-friendly

---

## Phase 5 — AI Image-to-List & Google Calendar

**Goal:** The two major integrations — AI-powered list extraction and shared family calendar.

### Part A: AI Image-to-List

1. **Service: Claude Vision API** (Anthropic SDK, `claude-sonnet-4-6`)
   - `app/services/ai_service.py` — send image + prompt, parse JSON response
   - `app/routers/ai.py` — `POST /v1/ai/image-to-list` (multipart: image + optional list_type hint)
2. **Flow:** capture photo → send to API → Claude extracts items as JSON → user sees editable preview → confirm → bulk add to list
3. **Rate limiting** — 10 requests/family/hour (Redis counter), log token counts for cost monitoring
4. **Error handling** — structured errors for malformed responses or illegible images
5. **Frontend**
   - `ImageCapture` — `getUserMedia` rear camera + `<input type="file" capture>` fallback
   - `ExtractedItemsPreview` — editable list before confirming
   - `AICaptureButton` — entry point in list UI

### Part B: Google Calendar Integration

1. **OAuth2 flow**
   - `GET /v1/calendar/auth/google` → redirect to Google consent (scope: `calendar.readonly`)
   - `GET /v1/calendar/auth/google/callback` → exchange code, encrypt tokens, store
   - State parameter = JWT with user_id (CSRF protection)
2. **Database: `google_oauth_credentials` table** — access_token + refresh_token encrypted at rest (Fernet), token_expiry, scope
3. **Alembic migration** `0004_create_oauth_credentials.py`
4. **Calendar endpoint** — `GET /v1/calendar/family/{familyId}/events?start=&end=`
   - Parallel async calls to Google Calendar API for each connected member
   - Merge results, label with member name + color
   - Cache in Redis for 5 minutes
5. **Frontend**
   - `/families/[familyId]/calendar` — weekly/monthly view
   - `FamilyCalendar` — using `@fullcalendar/react` (MIT, good mobile touch support)
   - `CalendarEvent` — color-coded by member
   - `ConnectGoogleCal` — prompt for unconnected members
6. **Tests** — AI: mock Anthropic SDK; Calendar: mock Google API

### End State
- Point phone at paper list → items appear in app
- Each family member connects Google Calendar → unified family view, color-coded
- Partial connection works (shows connected members only)

---

## Phase 6 — PWA Polish, Real-Time & Notifications

**Goal:** Transform from web app to genuine mobile experience.

### Deliverables

1. **PWA manifest** — name, icons (192x192, 512x512, apple-touch-icon), `display: standalone`, portrait orientation
2. **Service worker** (via `next-pwa`)
   - App shell: CacheFirst
   - API responses: NetworkFirst with cache fallback (lists load offline)
   - Images: StaleWhileRevalidate
   - Auth: NetworkOnly
3. **Install experience** — `InstallPrompt` component (iOS: manual instruction modal since `beforeinstallprompt` not supported)
4. **Offline support** — `OfflineBanner` when `navigator.onLine = false`, queued changes sync on reconnect
5. **Server-Sent Events** (upgrade from Phase 4 polling)
   - `GET /v1/families/{familyId}/lists/{listId}/stream` — SSE endpoint
   - Redis Pub/Sub as event bus: list item changes published → SSE clients notified
   - Frontend: TanStack Query cache invalidation on SSE events
6. **Push notifications** (Web Push Protocol + VAPID)
   - `push_subscriptions` table
   - Backend: `pywebpush` library
   - Triggers: chore assigned, chore completed (notify parent), new grocery item added
   - Frontend: permission request, subscription registration
7. **iOS-specific fixes** — meta tags for `apple-mobile-web-app-capable`, splash screens, test on iOS Simulator

### End State
- App installs to home screen on iOS + Android
- Lists load offline, changes sync when reconnected
- Real-time updates via SSE
- Push notifications for chore assignments/completions

---

## Phase 7 — Hardening, Testing & Production Readiness

**Goal:** Feature-complete → production-safe.

### Deliverables

1. **Comprehensive test suite**
   - Backend: unit (security, permissions, invite codes) + integration (full flows) — target 90% coverage
   - Frontend: unit (stores, utils) + integration (component flows)
   - E2E (Playwright): auth, family, lists, calendar — projects: `Mobile Chrome`, `Mobile Safari`
2. **Observability**
   - Error tracking: Sentry (`@sentry/nextjs` + `sentry-sdk[fastapi]`)
   - Logging: `structlog` for structured JSON logs
   - Metrics: Prometheus `/metrics` endpoint
   - Uptime: health check monitoring every 60s
3. **Security audit checklist**
   - All endpoints require auth (except health, register, login)
   - RLS active on all family tables
   - CORS strict allowlist (not `"*"`)
   - File uploads: MIME verified by reading file header bytes
   - OAuth tokens encrypted at rest
   - Rate limiting on auth + AI endpoints
   - CSP headers on all frontend responses
   - `pip audit` + `pnpm audit` in CI
   - No PII in logs
4. **Deployment pipeline finalization**
   - `deploy.yml`: test → deploy API (Railway) → deploy web (Vercel) → E2E against staging
   - Railway: `railway.toml` with `releaseCommand = "alembic upgrade head"`, health check
   - Vercel: `vercel.json` with security headers (X-Content-Type-Options, X-Frame-Options, CSP)
5. **Performance** — ensure p95 response times < 200ms for list operations

### End State
- 90%+ backend test coverage enforced in CI
- Sentry capturing errors in production
- Security checklist verified
- E2E tests run post-deploy against staging
- Zero-downtime deployments
- **App ready for real family use**

---

## Key Technology Decisions

| Decision | Choice | Why |
|---|---|---|
| Monorepo | pnpm + Turborepo | Caching, polyglot, simple config |
| Backend | FastAPI + SQLAlchemy 2.0 async | Async-native, Pydantic v2 integration |
| Migrations | Alembic | Industry standard for SQLAlchemy |
| Auth | JWT access (15min) + rotated refresh (30d) | Stateless access, revocable refresh |
| File storage | Cloudflare R2 (pre-signed URLs) | Zero egress, S3-compatible |
| AI OCR | Claude Vision (claude-sonnet-4-6) | Best handwriting recognition |
| Calendar | Google Calendar read-only OAuth2 | User requirement, minimal scope |
| Real-time | SSE via Redis Pub/Sub | Simpler than WebSockets, sufficient |
| Push | Web Push + VAPID | Works on iOS 16.4+ PWA |
| E2E testing | Playwright (mobile projects) | Best mobile emulation |
| Error tracking | Sentry | Industry standard, free tier |
