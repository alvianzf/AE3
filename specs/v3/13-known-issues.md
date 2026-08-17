# 13 · Known issues — v2.6

Produced by two independent reviews of the live deployment
(`https://telehealth.devshorepartners.id`) and the codebase — one acting
as PM (user flows, friction, unmet promises), one as QA (functional
defects, broken links, contract mismatches) — on 2026-08-14. Findings are
deduplicated where both reviews hit the same root cause.

**Status: all Critical and High findings fixed and deployed the same day.**
Medium/Low findings tied to email/notifications (M1, M4, L2) were
explicitly deferred — no email system exists in this codebase at all, and
building one was ruled out of scope for this pass. L1 (hard delete) is a
separate, already-tracked scope decision, not touched here.

Two of the critical findings (C1, C2) were live security/access-control
defects, not UX polish, flagged as such rather than softened to fit a
punch-list format.

---

## Critical

### C1 — Suspending a practitioner does not block their portal access — FIXED

**Live-confirmed.** `app/auth.py`'s `require_practitioner` checks only
`session["role"] == "practitioner"` — it never reads the practitioner's
`status` column. Reproduced: created a practitioner via the admin API,
suspended them (`POST /api/admin/practitioners/{id}/suspend`), logged in as
that account, and successfully called `GET /api/me/profile` and
`GET /api/me/contacts` — full access, unblocked.

[`specs/v2/04-admin-portal.md` §1](04-admin-portal.md#1-practitioner-management)
explicitly promises "Suspend: ... portal access blocked." It isn't.
`require_admin` gets this right (checks `is_active` against the DB on every
request, added specifically so a suspension takes effect immediately —
[10 · Security](10-security.md)); `require_practitioner` and
`require_client` never got the equivalent check.

**Fixed:** `require_practitioner` and `require_client` now check the live
DB, same pattern `require_admin` uses. `require_client` checks the
*practitioner's* status (their own vault has no status column, and a
client's access is meaningless without an active practitioner). Only
`status == "suspended"` blocks — `pending` intentionally still allows
login, since a newly-signed-up practitioner being able to log in and see
their own status is wanted behavior, not the bug that was found (login
itself also now blocks `suspended` accounts, matching admin's existing
precedent). Verified: suspend → immediate 401 on both API calls and fresh
login attempts; un-suspend restores access; a client's session 401s while
their practitioner is suspended.

### C2 — Client signup can silently take over an existing client's account — FIXED

**Code-confirmed; deliberately not executed against real data — the
takeover is irreversible from the API.** `POST /api/clients`
(`app/main.py`) branches on whether the submitted email already has a
`client_directory` entry. If it does, the handler treats this as "a Pro
practitioner pre-created this client, they're now completing their own
signup" and calls `vault.set_client_password()` with **no check that a
password isn't already set**, and no re-authentication of any kind.

The intended case (a Pro practitioner creates a client record with no
password, the real client "completes" it later) and the exploit case (an
attacker who merely knows a real client's email address) are
indistinguishable to this code — both just look like "an existing
`client_directory` entry, no password check performed." Anyone who knows or
guesses a client's email can silently reset their password and read their
questionnaire answers, uploaded files (lab results), and consultation
history.

**Fixed:** added a `password_set` column to vault `clients` (migrated via
`ALTER TABLE` for existing vaults, defaulting to 1 — every pre-existing
client already got their password some other way, so treating them as
"still pending" would be the wrong default). `POST /api/clients` now 409s
("An account with that email already exists. Please log in.") instead of
overwriting the password once that flag is set. A real invitation flow
(a signed, expiring token sent to the client) would be the more complete
fix but needs email (M1, deferred); the flag-check alone closes the hole
without it. Verified: the legitimate first completion still works, a
second attempt on the same email 409s, and the legitimately-set password
is unaffected by the rejected attempt.

### C3 — The Pro consultation feature has no UI — the paid feature cannot be used — FIXED

**Live-confirmed**, including against the demo Pro account provided for
this review. `POST /api/me/anthropic-key` exists and is exactly what
[07 · The AI team](07-ai-team.md) requires before a consultation can run,
but zero files under `static/` reference it — grepped for
`anthropic-key`/`anthropic_api_key` across the whole frontend, no hits.
`POST /api/me/consult` correctly 400s with "Set your Anthropic API key
before starting a consultation," but there is no field, button, or page
anywhere in the shipped UI that can satisfy that requirement.
`consult.html` will show a generic "Failed: ..." toast for every question a
Pro practitioner asks, with no indication why or what to do about it.

**Fixed:** added a key-entry panel to `/practitioner/profile` (Pro only,
write-only per [10 · Security](10-security.md)), and `consult.html`'s
error now links there when the 400 it gets is specifically the
no-key-on-file case.

---

## High

### H1 — The site-wide "Sign up" link is broken for its primary use case — FIXED

**Live-confirmed** (`400 "practitioner_id is required for a new client"`).
Every public page's topbar links plain `/signup`. `client-signup.html`
only reads a `practitioner_id` from a query string, which is only ever
populated when arriving via a specific coach's "Sign up as their client"
link on `/coach/{id}`. A visitor who clicks the nav "Sign up" directly —
the normal, expected path — can never complete signup.

This is also the root cause of [06 · Client
portal](06-client-portal.md)'s documented "picks a practitioner from the
directory themselves" path not existing: there is no practitioner picker on
`/signup` at all.

**Fixed:** `/signup` now shows a practitioner-select dropdown (populated
from `/api/practitioners`, filtered to Pro) whenever it's reached without a
`practitioner_id` query param, and refuses to submit without a selection.
The invite-completion path (arriving via `?practitioner_id=` from a coach
page) is unaffected.

### H2 — Coach pages show a "sign up as client" CTA that fails for every Basic-plan practitioner — FIXED

**Live-confirmed** (`400 "That practitioner cannot accept clients right
now."`). `coach.html` unhides its signup panel unconditionally, without
checking the `plan` field already present in the API response. Only Pro
practitioners can accept clients ([05 · Practitioner
portal](05-practitioner-portal.md)); a Basic practitioner's coach page
invites a visitor into a form that fails after they've filled it out. Not
currently visible in production only because the one approved practitioner
happens to be Pro — every new practitioner defaults to Basic, so this
surfaces the moment a second one is approved.

**Fixed:** `coach.html` only unhides the signup CTA when `p.plan === 'pro'`.

### H3 — Wearable connect redirects off-site to a broken authorize URL, stranding the user — FIXED

**Live-confirmed.** `POST /api/me/wearables/oura/connect` returns a real
`cloud.ouraring.com` authorize URL with an empty `client_id` (no OAuth app
credentials configured on this deployment — expected, since
[11 · Operations](11-operations.md) lists these as optional/not-yet-turned-on).
`wearables.html` does an unconditional `location.href` redirect regardless,
sending the user to a vendor page that will fail, with no way back into the
app. This also undercuts the page's own "sample data, nothing leaves the
app" framing — the OAuth handshake genuinely does leave the app, per
[06 · Client portal](06-client-portal.md)'s original design, even though
what happens after is fixture data.

**Fixed:** `POST /api/me/wearables/{provider}/connect` now 409s server-side
when that provider has no OAuth `client_id` configured, instead of handing
back a broken authorize URL — the frontend shows a toast instead of
redirecting. Also fixed while in this code: the OAuth callback previously
returned raw JSON directly to the vendor's browser redirect (stranding the
user on a bare API response even on success); it now redirects back to
`/client/wearables`, which re-fetches real state on load (see M2).

### H4 — Admin-created practitioner/admin passwords have no delivery mechanism — FIXED

An admin using `/admin/users`' "Add practitioner" or "Add admin" forms types
a password for someone else's account. After submit, only a toast confirms
creation — the password is never shown again, there's no copy-to-clipboard,
no forced-reset-on-first-login, and (per M1) no email. The admin must
remember what they typed and communicate it out-of-band, or the account is
effectively locked out immediately.

**Fixed:** `/admin/users` shows the email/password in a dismissible,
copy-buttoned panel immediately after either "Add practitioner" or "Add
admin" succeeds. Doesn't solve delivery to the practitioner themselves
(still out-of-band, still needs email per M1) — solves the admin's side:
they no longer have to remember what they typed.

### H5 — Admin website statistics have a full spec section and backend, but no UI — FIXED

[04 · Admin portal §4-5](04-admin-portal.md#4-website-statistics) promises
site-wide traffic/contact stats, per-practitioner views/contacts, and
per-practitioner client counts. `GET /api/admin/stats` and
`GET /api/admin/practitioners/{id}/client-count` both exist and work — no
page anywhere calls them. An admin has no visibility into how the business
is doing (traffic, leads, active client counts) through the UI at all.

**Fixed:** `/admin/users` gained a site-stats panel (`GET /api/admin/stats`)
and per-practitioner client/view/contact counts inline in the practitioner
list (fan-out per row, one call each — the scale this app is sized for
makes that fine, per [02 · Data model](02-data-model.md#cross-tenant-reads-the-admin-portal-needs)).

---

## Medium

### M1 — No email/notification system exists anywhere in the codebase — DEFERRED

Explicitly out of scope for the 2026-08-14 fix pass — no email system
exists, and building one wasn't part of that instruction. Still open.

`grep -rn "smtplib\|sendgrid\|mailgun\|SMTP" app/` returns nothing (still
true as of the fix pass). This silently breaks three things the spec says
happen:

- [03 · Website](03-website.md): a contact-form submission "Notifies the
  practitioner (email)" — it doesn't; the practitioner only finds out by
  manually checking `/practitioner/contacts`.
- [04 · Admin portal §1](04-admin-portal.md#1-practitioner-management): "the
  applicant is told" on rejection — nothing tells them.
- A Pro practitioner pre-creating a client (`POST /api/me/clients`) gets a
  "Client added" toast with no shareable link or instruction to pass along
  — the client has no way to discover their account exists.

**Fix direction (still open):** wire a real transactional email send (even
a minimal provider) for these three events, or explicitly re-scope the spec
language to stop promising notifications that don't exist.

### M2 — Wearable "connected" status is a client-side flag, not real state — FIXED

Already half-documented by a comment in `wearables.html` itself: there was
no `GET /api/me/wearables` status route, so the connected/not-connected
state lived only in `localStorage`. A client connecting from a second
device/browser saw "Connect" again for an already-connected provider.

**Fixed:** added `GET /api/me/wearables`, backed by the real
`wearable_connections` table (a new `vault.list_wearable_connections`
function — the table already existed, nothing read it). `wearables.html`
now fetches real state on every render instead of touching `localStorage`
at all.

### M3 — No way to view previously uploaded client files — FIXED

`POST /api/me/files` existed with no matching `GET`. `files.html` never
listed what had already been uploaded — a client had no way to confirm a
prior upload succeeded.

**Fixed:** added `GET /api/me/files` (client-facing, strips the internal
`storage_path` field before returning), and `files.html` now lists
previously uploaded files with their upload date. Not done: exposing the
same list on the practitioner's client-detail view — narrower fix than
originally scoped, left for a future pass.

### M4 — No proactive signal that a practitioner application was approved — DEFERRED

Tied to M1, not fixed this pass since it's fundamentally a notification
problem. Even with pull-based status-checking (a status chip already
renders on `/practitioner/profile`, and C1's login fix explicitly preserves
a pending practitioner's ability to log in and see it), nothing *prompts*
a newly-signed-up practitioner to go check. The only information they
receive at signup time is a toast that says to expect approval later — no
follow-up of any kind.

---

## Low

### L1 — No hard-delete for practitioner or client accounts — NOT TOUCHED

Already documented as a known gap in
[10 · Security](10-security.md#not-protected-carried-or-new) and
[11 · Operations](11-operations.md) — both reviews independently hit this
(suspend-only, no way to actually remove test/erroneous accounts) and
confirm it's accurate in production. Deliberately not touched this pass —
real account deletion is a separate scope/risk decision, not a quick fix.

### L2 — Contact form confirmation is a toast only, with no durable record for the sender — DEFERRED

Tied to M1 (no confirmation email) — an anonymous visitor still has no way
to later confirm their inquiry went through if they miss the toast.

### L3 — Practitioner Clients page copy promises a signup flow that doesn't exist — RESOLVED (via H1)

`clients.html`'s empty state reads "wait for a client to sign up and pick
you" — as of H1's fix, that flow now actually exists (`/signup`'s
practitioner picker). No separate change needed; this resolved as a side
effect.

---

## What was checked and found correct

Worth recording so a future pass doesn't re-litigate these: duplicate
signup (practitioner and client) correctly 409/400s with the error surfaced
to the user; wrong-password login correctly 401s; admin-only and Pro-only
routes correctly 401/403 for anonymous/under-privileged callers; a garbage
`/coach/{id}` degrades gracefully; `GET /api/practitioners/{id}` correctly
excludes `password_hash`/`anthropic_api_key_encrypted` (the v2.2 fix holds);
cross-tenant client access still 404s, not 403 or data; every `href` in
`static/` resolves to a real registered route (no dead links found); the
multipart-vs-JSON branch on `PUT /api/me/profile` handles both correctly
despite an uncertain code comment suggesting otherwise; the navigation
polish from v2.4/v2.5 (breadcrumbs, user menu, role-aware logo) is
consistent across every page checked.
