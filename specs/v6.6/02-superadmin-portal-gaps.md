# v6.6/02 — Superadmin-portal audit and fixes

**Status: implemented, live-verified in production.**

Same method as `01`, applied to the `(admin)` portal as a platform
operator: dashboard, users (practitioners/admins/clients), questionnaire
templates, audit log — cross-referenced against every `/api/admin/*`
and `/api/superadmin/*` route. Findings written to
`specs/known-superadmin-gaps.md` (living doc, not frozen here).

## Findings and fixes

1. **Admin-action audit trail was captured but had no read path.**
   `core_store.log()` already wrote a real Postgres `audit_events` row
   for every sensitive action (practitioner approve/reject/suspend,
   plan change, admin create/role-change/suspend/reactivate,
   questionnaire create/edit), but the only thing the Audit page called
   was a *different* table (Neo4j's library-only event log) —
   every admin-management decision was permanently unreadable through
   any UI. **Fixed**: `core_store.list_audit_events()`/
   `count_audit_events()`, a paginated `GET /api/superadmin/audit-log`,
   and a second section on the Audit page alongside the existing
   library-event log (not a replacement — both trails are real and
   distinct).
2. **Admin-account management existed on the backend with zero UI.**
   `POST /api/superadmin/admins`, role-change, suspend, and reactivate
   all worked (including correct last-superadmin-lockout protection)
   but the Admins tab only rendered a read-only table. **Fixed**: the
   same create/role-select/suspend/reactivate controls the Practitioners
   tab already had, mirrored onto the Admins tab — gated to
   `session.admin_role === 'superadmin'` on the frontend too, since a
   plain admin can reach the tab (the layout guard only checks
   `role === 'admin'`) and would otherwise see fully-interactive
   controls that just 403'd on click.
3. **No system/AI-pipeline health visibility in the admin UI.**
   `GET /api/health` already reported per-role AI-team status; nothing
   under `/admin/*` surfaced it. **Fixed**: a health panel on the admin
   dashboard (overall status + a chip per check with ping time or
   "down").
4. **Questionnaire builder silently discarded non-text question
   types.** Every question was hardcoded to `{prompt, input_type:
   'text'}` on save, and editing an existing typed/themed questionnaire
   round-tripped it through the same flattened textarea — a silent
   downgrade, since a new version replaces the old one outright.
   **Fixed**: a per-question type/theme/options editor that round-trips
   `input_type`/`options`/`theme` correctly.
5. **No client-account management at all.** Each client lives inside
   their own practitioner's vault schema (`app/vault.py`) with no
   central path to suspend one (an abuse report or legal request would
   have had no superadmin-level lever). **Fixed**: a new `active`
   column on `vault.py`'s `clients` table, `vault.set_client_active()`,
   `GET /api/admin/clients` (fans out across every pro practitioner's
   vault), `POST /api/admin/clients/{practitioner_id}/{client_id}/
   {suspend,reactivate}`, and a new Clients tab.
   - **Enforcement gap found and fixed while wiring this up**:
     `app/auth.py`'s client login branch and `require_client` didn't
     check this flag at all — a suspended client could still log in,
     and an already-logged-in one kept full portal access until their
     session cookie expired. Both now do a live check, the same pattern
     `require_admin`/`require_superadmin` already use so a suspension
     takes effect immediately rather than after a stale cookie.
6. **Practitioner list had no search and no per-row client-count.**
   `GET /api/admin/practitioners/{id}/client-count` existed with no
   caller. **Fixed**: a search box and a client-count column — the
   count is derived from the Clients tab's own already-fetched data
   (grouped by `practitioner_id`) rather than one extra round trip per
   practitioner.
7. **`/api/relink` and `/api/consolidate` had no UI trigger.** Both
   existed, admin-only, unreferenced anywhere in `web/src`. **Fixed**:
   buttons on the Library page, each behind a confirm dialog.

## Verification

`npm run check` — 0 errors. `python3 -m py_compile app/auth.py
app/main.py app/core_store.py app/vault.py` — clean. Reviewed via
`/code-review` before shipping; two findings fixed pre-merge (the
missing superadmin gate on finding 2, and the redundant per-practitioner
client-count calls on finding 6 — both described above as already
folded into the fix, not left as open items).
