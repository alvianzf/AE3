# v6.7/02 — Practitioner-owned questionnaires

**Status: implemented, live-verified in production.**

Questionnaires were previously a single global resource: one admin-
curated questionnaire, active or not, shared by every practitioner's
clients. Requested directly: practitioners should be able to create
their own, and separately, to activate/deactivate a questionnaire
without that being an implicit side effect of creating a new version.

## Data model change

`questionnaires.practitioner_id` (nullable, `REFERENCES practitioners`),
added via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` alongside the
existing `CREATE TABLE IF NOT EXISTS` (same migration pattern `v6.6`
used for `vault.py`'s `active` column on clients). `NULL` = the admin
default — every questionnaire that existed before this version keeps
working unchanged.

The "only one active questionnaire" invariant is now scoped to
`practitioner_id` (`IS NOT DISTINCT FROM`, to handle the `NULL` case
correctly) instead of global: one active admin default, and
independently, one active questionnaire per practitioner who has ever
created one.

`core_store.get_active_questionnaire(practitioner_id=None)` — a client
resolves to their own practitioner's active questionnaire first, falling
back to the admin default if the practitioner hasn't created (or has
deactivated) their own.

`core_store.set_questionnaire_active(id, active)` — new, explicit,
independent of versioning. Activating one deactivates every other
questionnaire in the same scope; deactivating just flips that one row
off (a scope can end up with zero active questionnaires — for a
practitioner that means their clients fall back to the admin default,
which is the intended behavior).

## Routes

- Admin: `POST /api/admin/questionnaires/{id}/{activate,deactivate}` —
  the builder previously had no explicit control at all, only implicit
  activation via creating a new version.
- Practitioner (`Pro`-only, `require_pro_practitioner`): full CRUD under
  `/api/me/questionnaires*` — list, get, create, edit (new version),
  activate, deactivate. Every write 404s (not 403) if the questionnaire
  isn't the caller's own, so a practitioner can't even confirm another
  practitioner's questionnaire exists.
- `GET /api/me/questionnaires` also returns the admin default alongside
  the caller's own (`include_admin_default` flag on
  `core_store.list_questionnaires`) — requested directly, same day as
  the initial build: **a practitioner can view the site default, just
  not edit it.** `GET /api/me/questionnaires/{id}` allows fetching the
  default too; edit/activate/deactivate remain strictly own-only.

## Frontend

- Admin builder (`admin/questionnaires/+page.svelte`) gained explicit
  Activate/Deactivate buttons, and an Owner column (`Admin default` /
  `Practitioner: <name>`) — multiple rows can now legitimately show
  "Active" at once (one per scope), which used to be unambiguous when
  only one questionnaire, ever, could be active (found in review).
- New practitioner-facing page (`practitioner/questionnaires/
  +page.svelte`, nav-gated `locked: !isPro`) — mirrors the admin
  builder's type/theme/options question editor exactly, talking to
  `/api/me/questionnaires*`. The site-default row renders with every
  field disabled and a View/Close dialog instead of Edit/Save — the
  backend already rejects the write, this just doesn't dangle a button
  that would fail.

## A real security gap found and fixed in review

The practitioner Library page also gained a document viewer this
session (`v6.7/03`), reusing `GET /api/sources/{id}/{text,original}`.
The first version gated those routes with a new
`require_admin_or_practitioner` that let *any* non-suspended
practitioner through — including Basic-plan accounts, and even
`pending`/`rejected` status, which `require_practitioner` still allows
to log in. The reasoning ("a practitioner already reads library content
via consults/weighting") only holds for Pro accounts — both of those
are `require_pro_practitioner`-gated. Fixed before merge: renamed to
`require_admin_or_pro_practitioner`, delegating to the real
`require_pro_practitioner` check rather than the looser one.

## Verification

`npm run check` clean, `python3 -m py_compile` clean on every touched
backend file. The scoping logic was verified live end-to-end against a
local Postgres instance: admin-default and practitioner-owned active
scopes confirmed independent (creating a practitioner's questionnaire
did not deactivate the admin default), client resolution and fallback
confirmed, explicit reactivation confirmed, admin-scope deactivation to
zero-active confirmed to leave a practitioner's own scope untouched.
Reviewed via `/code-review` before shipping (see above + `v6.7/03` for
the second finding fixed in the same pass).
