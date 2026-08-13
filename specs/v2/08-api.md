# 08 · HTTP API

JSON over HTTP, FastAPI, same conventions as v1
([v1/05-api.md](../v1/05-api.md)). What's new here is **real per-role auth**
replacing v1's single shared passphrase ([10](10-security.md)) — every route
below states which role(s) may call it.

Grouped by app, not exhaustively enumerated field-by-field; that level of
detail belongs in the API doc once each app's build starts, not guessed here
for endpoints that don't exist yet.

## Public (no auth)

| Route | Purpose |
|---|---|
| `GET /api/practitioners` | Directory list — `approved` only, filterable by specialty/language |
| `GET /api/practitioners/{id}` | Coach detail — 404 if not `approved` |
| `POST /api/practitioners` | Practitioner signup → `status=pending` |
| `POST /api/practitioners/{id}/contact` | Contact form submission |
| `POST /api/clients` | Client signup |
| `GET /api/health` | Liveness, open by design as in v1 |

## Practitioner (Basic or Pro, own resources only)

| Route | Purpose |
|---|---|
| `GET/PUT /api/me/profile` | Own public profile |
| `GET /api/me/contacts` | Contact form submissions addressed to them |
| `POST /api/me/upgrade` | Start Stripe checkout for Pro ([09](09-payments.md)) |

## Practitioner (Pro only)

| Route | Purpose |
|---|---|
| `POST /api/me/anthropic-key` | Set/rotate their own key — write-only, never read back |
| `GET/POST /api/me/clients` | Create/list their clients |
| `GET /api/me/clients/{id}` | Client record: entries, sessions, files, wearable data |
| `POST /api/me/consult` | Ask a question about a client — runs Librarian → Specialist → Checker with their key ([07](07-ai-team.md)) |

## Client

| Route | Purpose |
|---|---|
| `GET/POST /api/me/questionnaire` | Fetch active questionnaire, submit response |
| `POST /api/me/files` | Upload a lab file etc. |
| `POST /api/me/wearables/{provider}/connect` | Start OAuth flow |
| `GET /api/me/wearables/{provider}/callback` | OAuth callback → writes `wearable_connections`, seeds fixture data ([06](06-client-portal.md)) |

## Admin

| Route | Purpose |
|---|---|
| `GET /api/admin/practitioners` | Review queue + full roster, filterable by status |
| `POST /api/admin/practitioners/{id}/approve` `/reject` `/suspend` | Status transitions |
| `PUT /api/admin/practitioners/{id}/plan` | Basic ↔ Pro override |
| `…library routes` | Unchanged from v1 — `/api/sources`, `/api/graph`, `/api/relink`, `/api/consolidate` ([v1/05-api.md](../v1/05-api.md)) |
| `GET/POST /api/admin/questionnaires` | CRUD + versioning |
| `GET /api/admin/stats` | Site + per-practitioner traffic and contact-form stats |
| `GET /api/admin/practitioners/{id}/client-count` | Fans out to that practitioner's vault ([02](02-data-model.md)) |

## Failure modes

Same shape as v1: structured JSON error body, 401 for missing/invalid auth,
404 rather than a silent empty result for a resource that doesn't exist or
belongs to another tenant (a Pro practitioner requesting another
practitioner's client 404s, not 403 — existence of another tenant's client
id is not confirmed or denied).
