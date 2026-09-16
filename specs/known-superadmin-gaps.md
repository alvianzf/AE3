# Superadmin-portal audit — gaps found walking the app as a platform operator

Date: 2026-09-16
Method: read-only walkthrough of the `(admin)` portal (dashboard, users, questionnaires,
audit) cross-referenced against every `/api/admin/*` and `/api/superadmin/*` route in
`app/main.py`, and the underlying `app/core_store.py` logic they call. No code changed.

Ranked roughly by operational/safety impact.

---

## 1. Admin-action audit trail is captured but has no read path anywhere — HIGH

`core_store.log()` (`app/core_store.py:177`) writes a real Postgres `audit_events` row
for every sensitive admin/superadmin action: practitioner approved/rejected/suspended,
plan changed, admin created, admin role changed, admin suspended/reactivated,
questionnaire created/edited (`core_store.py:252,270,349,364,379,396,620,638`). This is
exactly the accountability trail a superadmin would need ("who approved this
practitioner," "who suspended this admin, and when").

There is no endpoint that reads this table back. `GET /api/audit` (`app/main.py:915-923`)
— the only thing the Admin portal's "Audit history" page (`admin/audit/+page.svelte`)
calls — is a *different* table entirely: Neo4j's library-only event log (`store.audit()`),
explicitly scoped by its own docstring to exclude this. The page's own hint text says as
much ("Library-only events... isn't shown here") but doesn't mention that the *other*
trail is being recorded and simply has no viewer. Every practitioner-approval and
admin-management decision this session is permanently unreadable through any UI or
existing API route — only a direct DB query would surface it.

## 2. Admin-account management exists on the backend with zero UI — HIGH

Four real, live backend capabilities have no button anywhere:
- `POST /api/superadmin/admins` — create a new admin (`app/main.py:1115`)
- `PUT /api/superadmin/admins/{id}/role` — promote/demote admin↔superadmin (`:1132`)
- `POST /api/superadmin/admins/{id}/suspend` (`:1144`)
- `POST /api/superadmin/admins/{id}/reactivate` (`:1156`)

`admin/users/+page.svelte`'s "Admins" tab (lines 111-123) only renders a read-only
`DataTable` (name/email/role) — no New-admin button, no suspend/reactivate action, no
role selector, unlike the parallel practitioner tab right next to it which has all of
these. Today the only way to onboard or manage a second admin account is a raw API call.
The backend logic here is actually well-built (see "not a gap" below) — the gap is
purely that the UI was never wired to it.

## 3. No system/AI-pipeline health visibility in the admin UI — MEDIUM

`GET /api/health` exists and reports per-role model status (already relied on
throughout this session's own model-routing work), but nothing under `/admin/*` surfaces
it — a superadmin has no way to see "is the Reasoner/Checker/Embedder actually up" without
curling the endpoint directly. `admin/dashboard/+page.svelte` renders whatever
`core_store.site_stats()` returns as generic tiles (practitioner/client/source counts,
presumably) — no AI-team or infrastructure health signal at all, even though this is the
one thing a real outage would need a fast, no-terminal way to check.

## 4. Questionnaire builder silently discards non-text question types — MEDIUM

`admin/questionnaires/+page.svelte:53-57` hardcodes every question as
`{ prompt, input_type: 'text' }` on save — the backend/client side already supports
`choice`/`multi_choice`/`number`/`date` and a `theme` grouping (confirmed in the parallel
client-portal audit, `specs/known-user-gaps.md`), but there is no way to author one
through this page. Worse, `openEdit` (lines 32-48) round-trips an *existing* questionnaire
through the same one-line-per-question textarea — editing and resaving a questionnaire
that already has typed/themed questions silently flattens them all to plain text
(new version replaces the old one outright, per `core_store._insert_questionnaire`
deactivating every prior row). There's no warning before that happens.

## 5. No client account management at all — MEDIUM

The Users page only has Practitioners/Admins tabs — no client-facing tab or search.
If a client account needs suspending (abuse, a support request, a legal request), there
is no superadmin path to do it; each practitioner's vault schema is per-practitioner
(`app/vault.py`), so a client can only be reached today by going through their specific
practitioner's own portal, not centrally. Worth naming explicitly since it's the kind of
gap that surfaces urgently (an abuse report) rather than gradually.

## 6. Practitioner list has no search and no per-row client-count/stat visibility — LOW

`GET /api/admin/practitioners/{id}/client-count` (`app/main.py:1272`) exists and returns
client count + stats, but `admin/users/+page.svelte`'s practitioner `DataTable` never
calls it — no client-count column, no way to tell which practitioners are actually
active vs. dormant without opening each one. Also no search/filter box on a table that
could grow past a quick scan (unlike the Library page, which has one). Low priority at
current practitioner-count scale, but the pattern's already inconsistent with the rest
of the admin UI.

## 7. `/api/relink` and `/api/consolidate` (graph-maintenance ops) have no UI trigger — LOW
Both exist (`app/main.py:782,811`, admin-only) and were presumably reachable from the
pre-rewrite admin page per this session's own established pattern of "backend route
existed before the SvelteKit rewrite, UI never got ported" (the same shape as the
regrade/delete gap the Library page's own comments cite as already-fixed,
`admin/+page.svelte:107-110`). Grepping the whole `web/src` tree found no reference to
either endpoint — if these are still operationally needed (deduping/relinking concepts),
they're curl-only today.

---

## Explicitly NOT gaps (checked and ruled out)

- **Last-superadmin protection**: `core_store.set_admin_active` and `set_admin_role`
  both correctly refuse to suspend/demote the last active superadmin
  (`core_store.py:263-265, 248-250`), raising a clear `ValueError` the route surfaces as
  a 400. Solid guardrail against a self-lockout, already in place.
- **Server-side role enforcement**: `auth.require_admin`/`require_superadmin`
  (`app/auth.py:73-96`) both do a live DB check on every request (not a cached session
  claim) specifically so a suspension or demotion takes effect immediately rather than
  after a stale 12h cookie expires — confirmed via the code comments citing this as a
  deliberate fix from an earlier review (`specs/v4/04-known-issues.md#c9`). The
  `(admin)/admin/+layout.ts` client-side redirect is a UX nicety on top of this, not the
  actual boundary.
- **Suspend/reject confirmation dialogs** (practitioners): both actions share one
  confirm dialog (`admin/users/+page.svelte:33-51`) — already fixed per an earlier
  review (`specs/v4/04-known-issues.md#l3`), not a live gap.
- **Practitioner status transitions**: approve/reject/suspend/re-approve all map to real,
  distinct backend states (`app/core_store.py` practitioner status columns) with no dead
  ends — a rejected or suspended practitioner can always be re-approved.
