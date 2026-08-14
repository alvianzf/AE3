# 08 · HTTP API

JSON over HTTP, FastAPI, same conventions as v1
([v1/05-api.md](../v1/05-api.md)). What's new here is **real per-role auth**
replacing v1's single shared passphrase ([10](10-security.md)) — every route
below states which role(s) may call it. Reflects what's actually
implemented and deployed, not a plan — see [12](12-verification.md) for how
it was proven.

## Page routes vs. API routes

Two separate route families, easy to conflate:

- **Page routes** (`GET /login`, `/directory`, `/coach/{id}`,
  `/practitioner/profile`, `/client/questionnaire`, `/admin`, `/admin/users`, …) serve the
  static HTML pages under `static/`. They carry no `/api` prefix and no
  `/static/public|practitioner|client` segment — the directory layout on
  disk is not exposed in the URL. `/static/*` itself is mounted only for the
  page's own assets (`style.css`, `shared.js`, `app.js`), not as an
  alternate way to reach a page.
- **API routes** (below, all under `/api/`) are what those pages' JS calls.

`GET /` redirects to `/login`.

## Public (no auth)

| Route | Purpose |
|---|---|
| `GET /api/practitioners` | Directory list — `approved` only, filterable by specialty/language |
| `GET /api/practitioners/{id}` | Coach detail — 404 if not `approved` |
| `POST /api/practitioners` | Practitioner signup (multipart, for the photo) → `status=pending` |
| `POST /api/practitioners/{id}/contact` | Contact form submission |
| `POST /api/clients` | Client signup — attaches to `practitioner_id` if new, or completes an existing practitioner-created invite by email |
| `POST /api/auth/login` | `{email, password}` → sets the session cookie; role is resolved server-side (tries admin, then practitioner, then client), never chosen by the caller |
| `POST /api/auth/logout` | Clears the session cookie |
| `POST /api/stripe/webhook` | Stripe webhook — verified by signature, not a session ([09](09-payments.md)) |
| `GET /api/me/wearables/{provider}/callback` | OAuth callback — verified by a signed `state` param, not a session |
| `GET /api/health` | Liveness, open by design as in v1 |

## Any authenticated role

| Route | Purpose |
|---|---|
| `GET /api/auth/me` | Current session `{role, id}`, or 401 |
| `POST /api/auth/change-password` | `{current_password, new_password}` — works for whichever role is signed in, verified against that role's own store before setting a new hash. Added after initial deploy: v1 had a shared passphrase with nothing to rotate; v2's real accounts needed a way to change one and none existed until this route. |

## Practitioner (Basic or Pro, own resources only)

| Route | Purpose |
|---|---|
| `GET/PUT /api/me/profile` | Own public profile — PUT accepts JSON or multipart (photo) |
| `GET /api/me/contacts` | Contact form submissions addressed to them, filterable by status |
| `PATCH /api/me/contacts/{id}` | Mark a submission contacted/closed |
| `POST /api/me/upgrade` | Start Stripe checkout for Pro ([09](09-payments.md)) |
| `GET /api/me/billing-portal` | Stripe Billing Portal link (Pro only in practice — no active subscription without one) |

## Practitioner (Pro only)

| Route | Purpose |
|---|---|
| `POST /api/me/anthropic-key` | Set/rotate their own key — write-only, never read back |
| `GET/POST /api/me/clients` | Create/list their clients |
| `GET /api/me/clients/{id}` | Client record: entries, sessions, files, wearable data |
| `DELETE /api/me/clients/{id}` | Erase a client — redacts vault audit detail, keeps the rows ([10](10-security.md)) |
| `POST /api/me/consult` | Ask a question about a client — runs Librarian → Specialist → Checker with their key ([07](07-ai-team.md)); 400 if no key is on file yet |
| `GET /api/me/clients/{id}/sessions` | List a client's consultations (v2.7), newest first, with `status` and turn count |
| `GET /api/me/clients/{id}/sessions/{session_id}` | Full turn transcript + both documents (`clinician_note`, `client_report`) for one consultation (v2.7) |
| `PATCH /api/me/clients/{id}/sessions/{session_id}/status` | Toggle `in_progress` ↔ `done` (v2.7) |
| `PUT /api/me/clients/{id}/sessions/{session_id}/documents/{kind}` | Save a `clinician_note` or `client_report` as `draft` or `final` (v2.7) |
| `GET /api/me/clients/{id}/documents` | All documents across a client's sessions, newest first — the reports & documents panel (v2.7) |
| `GET /api/me/clients/{id}/intake` | Client's questionnaire response + the questionnaire structure (with themes) + saved clinician notes per theme (v2.7) |
| `PUT /api/me/clients/{id}/intake/notes` | Upsert one clinician note for one theme (v2.7) |
| `GET /api/me/knowledge` | The shared library merged with this practitioner's own source weight overrides (v2.7) |
| `PUT /api/me/knowledge/{source_id}/weight` | Set this practitioner's personal weight (1-10) for a source — stored in their own vault, never touches the admin grade (v2.7) |
| `GET /api/me/sessions/recent` | Most recent consultations across every client, joined with client name — the dashboard's historical-consultations widget (v2.8) |

## Client

Every client-scoped route resolves the practitioner's vault from the
session's `practitioner_id` claim (set at login, since `vault.py` shards by
practitioner) — never from a request parameter.

| Route | Purpose |
|---|---|
| `GET/POST /api/me/questionnaire` | Fetch active questionnaire, submit response |
| `GET /api/me/questionnaire/response` | The client's own submitted response, or `null` — the client dashboard's questionnaire-status card (v2.8) |
| `POST /api/me/files` | Upload a lab file etc. |
| `POST /api/me/wearables/{provider}/connect` | Start OAuth flow, `practitioner_id` from the session |

## Admin

| Route | Purpose |
|---|---|
| `GET /api/admin/practitioners` | Review queue + full roster, filterable by status |
| `POST /api/admin/practitioners` | Admin creates a practitioner directly — `approved` immediately, unlike public signup's `pending` |
| `POST /api/admin/practitioners/{id}/approve` `/reject` `/suspend` | Status transitions — `approve` also works from `rejected`/`suspended` (reactivation) |
| `PUT /api/admin/practitioners/{id}/plan` | Basic ↔ Pro override — setting `pro` calls the same `activate_pro()` Stripe's webhook calls, so Pro can be granted without Stripe ([09](09-payments.md)) |
| `…library routes` | Unchanged from v1 — `/api/sources`, `/api/graph`, `/api/relink`, `/api/consolidate`, `/api/coverage`, `/api/audit` (library-only, not merged with any vault — [10](10-security.md)) ([v1/05-api.md](../v1/05-api.md)) |
| `GET/POST /api/admin/questionnaires` | List / create. `POST /api/admin/questionnaires/{id}` creates a new version rather than editing in place |
| `GET /api/admin/questionnaires/{id}` | Fetch one questionnaire with its questions (v2.7 — backs the builder's edit view) |
| `GET /api/admin/stats` | `{total_views, total_contacts}` site-wide |
| `GET /api/admin/practitioners/{id}/client-count` | Fans out to that practitioner's vault ([02](02-data-model.md)); `0` for Basic |

**Not built**: a route to delete a practitioner outright (only suspend —
[10](10-security.md) records this as a known gap), and a route exposing a
Pro practitioner's own vault audit trail to either the practitioner or the
admin.

## Superadmin

Added after initial deploy — see
[04 · Admin portal §0](04-admin-portal.md#0-superadmin-vs-admin) and
[10 · Security](10-security.md) for why. Every route here 403s for a
regular `admin` session.

| Route | Purpose |
|---|---|
| `GET /api/superadmin/admins` | List all admin accounts, both tiers |
| `POST /api/superadmin/admins` | Create an admin or superadmin account |
| `PUT /api/superadmin/admins/{id}/role` | Promote/demote — 400 if it would leave zero active superadmins |
| `POST /api/superadmin/admins/{id}/suspend` `/reactivate` | Blocks/restores login and, for an already-active session, every `require_admin` route on the next request — 400 on `/suspend` if it would leave zero active superadmins |

## Failure modes

Same shape as v1: structured JSON error body, 401 for missing/invalid auth,
404 rather than a silent empty result for a resource that doesn't exist or
belongs to another tenant (a Pro practitioner requesting another
practitioner's client 404s, not 403 — existence of another tenant's client
id is not confirmed or denied). Verified live in [12](12-verification.md).
