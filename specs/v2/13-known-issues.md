# 13 · Known issues — v2.6 backlog

**Status: planned, not built.** Unlike every other doc in this version,
this one describes what v2.6 *should* fix, not what shipped. Produced by
two independent reviews of the live deployment
(`https://telehealth.devshorepartners.id`) and the codebase — one acting
as PM (user flows, friction, unmet promises), one as QA (functional
defects, broken links, contract mismatches) — on 2026-08-14. Findings are
deduplicated where both reviews hit the same root cause.

Two of these (C1, C2) are live security/access-control defects, not
UX polish, and are flagged as such rather than softened to fit a punch-list
format.

---

## Critical

### C1 — Suspending a practitioner does not block their portal access

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

**Fix direction:** `require_practitioner` should 401 unless
`core_store.get_practitioner(id)["status"] == "approved"`, same live-DB-check
pattern `require_admin` already uses. `require_client` needs the equivalent
against the vault's client row (no `status` column exists there yet —
would need one, or reuse the practitioner's own status transitively since a
client's access is meaningless without their practitioner active).

### C2 — Client signup can silently take over an existing client's account

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

**Fix direction:** the pre-created-but-passwordless state needs to be
distinguishable from an already-active account — e.g. a sentinel value or a
new `password_set` flag on the vault `clients` row — and `POST /api/clients`
must refuse to touch the password once that flag is true. A real invitation
flow (a signed, single-use, expiring token sent to the client, per C-adjacent
finding M1's email gap) is the more complete fix but the flag-check alone
closes the hole.

### C3 — The Pro consultation feature has no UI — the paid feature cannot be used

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

**Fix direction:** add a key-entry field (write-only, matching
[10 · Security](10-security.md)'s "never returned by any read endpoint"
rule) to `/practitioner/profile` or a dedicated settings section, and have
`consult.html` detect the specific 400 and link there instead of a bare
toast.

---

## High

### H1 — The site-wide "Sign up" link is broken for its primary use case

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

**Fix direction:** add a practitioner-select control to `/signup` when no
`practitioner_id` is present (searchable list, same data `/directory`
already fetches), or point the nav's plain "Sign up" link at `/directory`
so every real path to signup carries a practitioner id.

### H2 — Coach pages show a "sign up as client" CTA that fails for every Basic-plan practitioner

**Live-confirmed** (`400 "That practitioner cannot accept clients right
now."`). `coach.html` unhides its signup panel unconditionally, without
checking the `plan` field already present in the API response. Only Pro
practitioners can accept clients ([05 · Practitioner
portal](05-practitioner-portal.md)); a Basic practitioner's coach page
invites a visitor into a form that fails after they've filled it out. Not
currently visible in production only because the one approved practitioner
happens to be Pro — every new practitioner defaults to Basic, so this
surfaces the moment a second one is approved.

**Fix direction:** `coach.html` should hide or relabel the signup CTA when
`p.plan !== 'pro'`.

### H3 — Wearable connect redirects off-site to a broken authorize URL, stranding the user

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

**Fix direction:** either configure real (sandbox) OAuth credentials before
enabling the connect buttons, or have the frontend detect that a provider
isn't configured and disable/hide its Connect button rather than redirecting
into a dead end.

### H4 — Admin-created practitioner/admin passwords have no delivery mechanism

An admin using `/admin/users`' "Add practitioner" or "Add admin" forms types
a password for someone else's account. After submit, only a toast confirms
creation — the password is never shown again, there's no copy-to-clipboard,
no forced-reset-on-first-login, and (per M1) no email. The admin must
remember what they typed and communicate it out-of-band, or the account is
effectively locked out immediately.

**Fix direction:** show/copy the password once immediately after creation
in the UI, or switch to generating a reset link instead of accepting a
plaintext password from the admin at all.

### H5 — Admin website statistics have a full spec section and backend, but no UI

[04 · Admin portal §4-5](04-admin-portal.md#4-website-statistics) promises
site-wide traffic/contact stats, per-practitioner views/contacts, and
per-practitioner client counts. `GET /api/admin/stats` and
`GET /api/admin/practitioners/{id}/client-count` both exist and work — no
page anywhere calls them. An admin has no visibility into how the business
is doing (traffic, leads, active client counts) through the UI at all.

**Fix direction:** add a stats panel to `/admin/users` (the natural home,
alongside practitioner management) or a new `/admin/stats` page.

---

## Medium

### M1 — No email/notification system exists anywhere in the codebase

`grep -rn "smtplib\|sendgrid\|mailgun\|SMTP" app/` returns nothing. This
silently breaks three things the spec says happen:

- [03 · Website](03-website.md): a contact-form submission "Notifies the
  practitioner (email)" — it doesn't; the practitioner only finds out by
  manually checking `/practitioner/contacts`.
- [04 · Admin portal §1](04-admin-portal.md#1-practitioner-management): "the
  applicant is told" on rejection — nothing tells them.
- A Pro practitioner pre-creating a client (`POST /api/me/clients`) gets a
  "Client added" toast with no shareable link or instruction to pass along
  — the client has no way to discover their account exists.

**Fix direction:** wire a real transactional email send (even a minimal
provider) for these three events, or explicitly re-scope the spec language
to stop promising notifications that don't exist.

### M2 — Wearable "connected" status is a client-side flag, not real state

Already half-documented by a comment in `wearables.html` itself: there's no
`GET /api/me/wearables` status route, so the connected/not-connected state
lives only in `localStorage`. A client connecting from a second
device/browser sees "Connect" again for an already-connected provider.

**Fix direction:** add the missing GET route, backed by the real
`wearable_connections` table that already exists.

### M3 — No way to view previously uploaded client files

`POST /api/me/files` exists; there's no matching `GET`. `files.html` never
lists what's already been uploaded — a client (or their practitioner) has
no way to confirm a prior upload succeeded or see the history.

**Fix direction:** add `GET /api/me/files` (client) and expose uploaded
files on the practitioner's client-detail view.

### M4 — No proactive signal that a practitioner application was approved

Tied to M1 but distinct: even with pull-based status-checking (a status
chip already renders on `/practitioner/profile` per C1's finding that login
isn't blocked by status), nothing *prompts* a newly-signed-up practitioner
to go check. The only information they receive at signup time is a toast
that says to expect approval later — no follow-up of any kind.

---

## Low

### L1 — No hard-delete for practitioner or client accounts

Already documented as a known gap in
[10 · Security](10-security.md#not-protected-carried-or-new) and
[11 · Operations](11-operations.md) — both reviews independently hit this
(suspend-only, no way to actually remove test/erroneous accounts) and
confirm it's accurate in production. Not re-opening as new; referenced here
so it's visible in the same backlog as everything else.

### L2 — Contact form confirmation is a toast only, with no durable record for the sender

Reasonable as immediate feedback, but combined with M1 (no confirmation
email), an anonymous visitor has no way to later confirm their inquiry went
through if they miss the toast.

### L3 — Practitioner Clients page copy promises a signup flow that doesn't exist

`clients.html`'s empty state reads "wait for a client to sign up and pick
you" — the flow H1 shows doesn't currently exist in the UI. Same root
cause as H1; will resolve once H1 does.

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
