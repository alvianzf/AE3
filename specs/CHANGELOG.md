# Specs changelog

## v2.12 — 2026-08-14 (remaining v2.7 findings closed out — A1-A4, C2, C3, S1-S4)

All 20 findings from [14 · UX findings](v2/14-ux-findings-v2.7.md) are now
resolved.

**Admin:**
- **A1** — saving a questionnaire edit that isn't already the active one now
  asks for confirmation first ("Saving will make this the active
  questionnaire, replacing the one clients currently answer. Continue?"),
  since it silently changes what every client sees.
- **A2** — the active questionnaire is now pinned in its own "currently
  active" card above a "Previous versions" list, instead of one flat list
  where every row looked equally current.
- **A3** — `/admin` (the knowledge-library dashboard) gained the same
  "Admin / …" breadcrumb its sibling pages already had.
- **A4** — the "Account created" credentials panel now renders inside the
  form that created the account (`#np-credentials-slot` /
  `#na-credentials-slot`), not at page-top — adding a practitioner or admin
  no longer reflows Site statistics and the roster list underneath it.

**Client:**
- **C2** — the wearable connect button shows "Redirecting…" between the API
  response and the browser navigating to the vendor, instead of just
  sitting disabled with no explanation.
- **C3** — the no-active-questionnaire empty state now links to Files and
  Wearables, matching the post-submit state's "next steps" links.

**Public/shared:**
- **S1** — public pages (`about`, `directory`, `coach`, both signup flows,
  the practitioner thank-you page) now check for a session on load and
  swap "Sign up"/"Log in" for a single "Go to my dashboard" link when one
  exists, via a new `adaptPublicAuthLinks()` helper in `shared.js`.
- **S2** — `/account` gained a "Back to my portal" sidebar link and its
  logo now points at the signed-in role's own dashboard instead of the
  public directory — previously it was a dead end reachable only by the
  browser's back button.
- **S3** — the mobile (≤900px) sidebar drops the tagline/tag pill so nav
  links surface sooner, and gets an edge-fade mask signaling the row
  scrolls further.
- **S4** — the practitioner thank-you page's copy now says Upgrade is "the
  Upgrade page in your sidebar," matching where it actually lives.

## v2.11 — 2026-08-14 (proactive API-key banner; add-client form open when empty)

Resolves [14 · UX findings](v2/14-ux-findings-v2.7.md) P7 and P9.

- **Consult shows a banner** ("Set your Anthropic API key to start
  consulting") whenever a Pro practitioner has no key on file, as soon as
  the page loads — not only after they've already typed a question and hit
  the 400 from `POST /api/me/consult`.
- **"Add a client" opens by default** on `/practitioner/clients` when the
  list is empty — a brand-new Pro practitioner's single most useful action
  on that page no longer starts hidden behind a collapsed `<details>`.

## v2.10 — 2026-08-14 (documents panel jumps to its session; note vs. report distinguished)

Resolves [14 · UX findings](v2/14-ux-findings-v2.7.md) P5 and P6.

- **Reports & documents rows are clickable** (`client-detail.html`): clicking
  one switches to the Consultations & reports tab, expands that document's
  parent session if it wasn't already open, scrolls it into view, and
  briefly outlines it — previously the panel was a flat, unclickable list
  and finding the source session meant scrolling and matching manually.
- **Clinician note vs. client report now visually distinguished by
  audience**: each gets a left border accent and an explicit "Internal —
  only you can see this" / "Shared with the client" label, instead of two
  identically-weighted textareas side by side with only their heading text
  to tell them apart.

## v2.9 — 2026-08-14 (Consult shows everything about the selected client)

Resolves [14 · UX findings](v2/14-ux-findings-v2.7.md) P1-P4: a practitioner
had to leave Consult to check a client's intake or history, and nothing
linked the two pages together.

- **Client overview panel** on `/practitioner/consult`, next to the ask
  panel whenever a client is selected: their questionnaire answers grouped
  by theme (same data as the intake review tab) and their 5 most recent
  consultations with status — all without navigating away.
- **`?client=<id>` and `?session=<id>` query params**: `client-detail.html`'s
  "Start consultation" button and each session's new "Continue in Consult"
  link now carry real context into Consult, which reads them on load and
  auto-selects the client (and replays that session's transcript into the
  thread if a session id is present) instead of landing on the generic
  picker. Consult also keeps the URL in sync as a client is selected, so
  a consultation-in-progress can be bookmarked or shared.
- **Renamed "Resume" → "Reopen"** on the done/in-progress toggle in
  `client-detail.html`'s session list, since "Resume" now means something
  different (continue chatting in Consult) — the two were easy to conflate
  under one label.

Dashboard layouts also switched from multi-column card grids to a single
stacked column — the grids left visible empty space with only 2-3 cards.

## v2.8 — 2026-08-14 (dashboards for every portal)

Each portal (admin, practitioner, client) gets a `Dashboard` page — an
overview landing screen, first item in that portal's sidebar, and now the
default page after login (`LANDING` map in `static/public/login.html`).

- **Admin dashboard** (`/admin/dashboard`): site stats, a pending-applications
  quick list linking into `/admin/users`, and a knowledge-library summary
  (topics covered, source-topic tags, passages) via the existing
  `GET /api/coverage`.
- **Practitioner dashboard** (`/practitioner/dashboard`): plan/status/API-key
  chips, a contact-submissions count, a client count (Pro), recent new
  contact submissions, and a **historical consultations** widget — each row
  shows a calendar-style date marker (large day number, 3-letter month
  below it) instead of a plain timestamp, linking into that client's detail
  page. Backed by a new `vault.list_recent_sessions()` / `GET
  /api/me/sessions/recent`, joining `sessions` with `clients` for the name
  in one query rather than fanning out per client.
- **Client dashboard** (`/client/dashboard`): questionnaire submission
  status (new `GET /api/me/questionnaire/response`), file count, and
  wearable-connection count, each linking to its own page.
- **Practitioner sidebar reordered**: Dashboard first, Consult second
  (unchanged from v2.7's decision to make Consult the entry point — Dashboard
  now sits above it as the true landing page).
- **Knowledge base weight control** (`/practitioner/knowledge`, from v2.7) is
  now a slider and a number input kept in sync, not a number input alone.
- **Account dropdown icon changed to a lock**, distinguishing it from the
  Profile item's person icon — Account is specifically where credentials
  (password) are managed, a lock reads more accurately than a second
  person icon next to Profile's.

## v2.7 — 2026-08-14 (client history/reports, themed intake, sidebar nav)

Three previously-unspecified feature requests, scoped down before building
([02](v2/02-data-model.md), [04](v2/04-admin-portal.md),
[08](v2/08-api.md)): an admin questionnaire builder with mixed question
types and themes, a themed "Intake review" for practitioners (no AI
synthesis yet — deferred as its own follow-up), and a per-client
consultation history with draft/final clinician notes and client reports.

**Admin — questionnaire builder** (`/admin/questionnaires`): create/edit
questionnaires with mixed question types (text, number, date, choice,
checklist) grouped into themes (`questionnaire_questions.theme`, migrated).
Editing still creates a new version rather than mutating in place, unchanged
from v1's rule. Added `GET /api/admin/questionnaires/{id}` to back the
builder's edit view.

**Practitioner — client detail page** (`/practitioner/clients/{id}`, new):
- *Intake review* tab — a client's questionnaire answers grouped by theme,
  with a free-text clinician-notes box per theme (`intake_notes` table, new).
- *Consultations & reports* tab — past consultations with `in_progress`/
  `done` status (`sessions.status`, migrated), expandable Q&A turns, and two
  documents per consultation — a Clinician note and a Client report, each
  independently draft/final (`session_documents` table, new) — plus a
  Reports & documents panel listing every document across a client's
  sessions.
- Six new practitioner-scoped routes under `/api/me/clients/{id}/...` for
  sessions, session status, documents, and intake notes/notes-save.

**Fixed same day, before any real client data depended on it:** the client
questionnaire's submit handler keyed answers by prompt text; Intake review
reads them by question id. Every answer would have shown "not answered."
Found by a PM-agent UX audit, fixed by keying both sides on question id.

**Navigation redesigned:** page-navigation links moved from the top bar into
a left sidebar on every authenticated/portal page; the account/logout menu
stays in a slim top strip. Auth flows (login, both signups, the
practitioner-signup thank-you page) and the client questionnaire page keep
the plain top bar instead — single-task screens where a persistent portal
sidebar is a distraction, not an aid. Practitioner's default landing page
changed from Profile to Consult.

**Specced, not yet built:** a follow-up UX audit (PM agent → Engineer)
produced [14 · UX findings v2.7](v2/14-ux-findings-v2.7.md) — 20 findings
across all four portals (e.g. "Start consultation" doesn't carry client
context into Consult; `/account` has no way back to your own portal). None
of these are implemented yet; sequencing which ones to build is a separate
decision.

## v2.6 — 2026-08-14 (PM+QA review, all Critical/High findings fixed)

Two independent reviews (PM: user flows and unmet promises; QA: functional
defects and broken links) of the live deployment produced
[13 · Known issues](v2/13-known-issues.md) — 3 critical, 5 high, 4 medium,
3 low findings. All Critical and High findings were fixed and deployed the
same day; email-dependent Medium/Low findings were explicitly deferred (no
email system exists in this codebase, building one was out of scope).

**Fixed — Critical:**
- A suspended practitioner's portal access wasn't actually blocked —
  `require_practitioner`/`require_client` now check live status against
  the database, same pattern `require_admin` already used. Login itself
  now blocks `suspended` accounts too; `pending` still allows login on
  purpose (seeing your own status is wanted behavior).
- `POST /api/clients` could silently overwrite an existing client's
  password with no auth check — closed with a `password_set` flag on the
  vault `clients` row (migrated for existing vaults); a second signup
  attempt on an already-active email now 409s instead of succeeding.
- The Pro consultation feature had no UI to set an Anthropic key anywhere
  — added a key-entry panel to `/practitioner/profile`; `consult.html`'s
  error now links there instead of a bare toast.

**Fixed — High:** the site-wide "Sign up" link now shows a practitioner
picker instead of 400ing; coach pages only show the signup CTA for Pro
practitioners; wearable connect 409s instead of redirecting to a dead
OAuth URL when a provider isn't configured (and the OAuth callback now
redirects back into the app instead of leaving a bare JSON response);
admin-created passwords are shown once in a copyable panel;
`/admin/users` gained a site-stats panel and per-practitioner
client/view/contact counts.

**Fixed — Medium (partial):** real wearable connection state
(`GET /api/me/wearables`, replacing a `localStorage`-only guess) and a
file list on `/client/files` (`GET /api/me/files`).

**Deferred:** everything tied to email/notifications, and hard account
deletion (a separate scope/risk decision). See
[13](v2/13-known-issues.md) for exactly what's still open.

## v2.5 — 2026-08-13 (navigation polish, round two)

- **User menu trigger redesigned**: a circular avatar-style icon + separate
  chevron, not a rectangular button — v2.4 shipped it styled as one more
  `.btn` alongside the nav's other buttons, which read as just another
  action rather than "this is your account."
- **Logo links to your own section**, not `/` — `/admin`, `/practitioner/profile`,
  `/client/questionnaire`, or `/directory` depending which app you're in.
  `/` still exists and still redirects to `/login`, but nothing links to
  it anymore except direct navigation.
- **Status readout moved to a footer** on the admin dashboard, out of the
  topbar.

See [03](v2/03-website.md#shared-navigation-conventions) for the updated
conventions. No API changes — presentation-layer only, same as v2.4.

## v2.4 — 2026-08-13 (navigation polish)

- **Breadcrumbs** on every page with real hierarchy — `/admin/users`, the
  five `/practitioner/*` pages, the three `/client/*` pages. Skipped on
  single-level pages (about, login, directory, …) where a one-item trail
  is noise, not navigation.
- **User menu.** The separate "Account" link and "Log out" button in every
  topbar are now one icon+chevron button that opens a small dropdown
  containing both, rather than two adjacent buttons — see
  [03](v2/03-website.md#shared-navigation-conventions).

No API changes — both are presentation-layer only.

## v2.3 — 2026-08-13 (dedicated user-management page)

- **`POST /api/admin/practitioners`** — admin or superadmin creates a
  practitioner directly, approved immediately rather than entering the
  pending review queue ([04](v2/04-admin-portal.md#1-practitioner-management)).
- **New `/admin/users` page**, split out of `/admin`'s knowledge-library
  dashboard: practitioner list/filter/actions/create for any admin, plus an
  admin-management section (moved from `/admin`, unchanged) visible only to
  superadmin sessions.
- Every practitioner and client page was missing a link to `/account` —
  there was no way to reach password-change from them. Added, along with
  icons on every Account link and Log out button site-wide.

## v2.2 — 2026-08-13 (superadmin hierarchy + a real production leak)

Also same version, more post-deploy corrections.

- **Superadmin/admin split** ([04](v2/04-admin-portal.md#0-superadmin-vs-admin),
  [10](v2/10-security.md)). v2 originally shipped with one undifferentiated
  admin role and no way to create a second admin account — a real gap once
  live, not a hypothetical one. `superadmin` adds exactly one capability
  over `admin`: creating/promoting/demoting/suspending other admin
  accounts. Guarded so the last active superadmin can never be
  demoted/suspended.
- **Fixed a live password-hash leak** ([10](v2/10-security.md#the-leak-that-was-found)).
  `GET /api/practitioners/{id}` — public, unauthenticated — was returning
  every practitioner's bcrypt `password_hash`; eight other routes leaked it
  or `anthropic_api_key_encrypted` to authenticated callers. Found while
  testing the superadmin routes (which had the same bug), fixed the same
  day across all nine routes. Recorded in full per the same "write down the
  leak" precedent v1 set.
- Admin dashboard (`/admin`) got a logout button it never had, and an
  already-logged-in visitor to `/login` now redirects straight to their
  dashboard instead of re-prompting for credentials.

## v2.1 — 2026-08-13 (post-deploy fixes)

Same version, no new scope — corrections made after v2 went live at
https://telehealth.devshorepartners.id, tracked here rather than silently
folded into the v2 entry below since the spec was already "finalized" when
these were found.

- **Retired the rest of v1's UI.** `/` used to serve v1's combined SPA
  unauthenticated; it now redirects to `/login`. The SPA's old
  "Practitioner" tab (patient records, consult) called `/api/patients` and
  `/api/consult`, both retired when v2 shipped — deleted rather than left
  broken, along with the now-fully-unused `app/gate.py` and
  `app/patients.py`.
- **Added `POST /api/auth/change-password`** ([08](v2/08-api.md#any-authenticated-role))
  and an account settings page — v1's shared passphrase had nothing to
  rotate; v2's real accounts needed a way to and none existed until this.
- **Clean top-level page routes** ([03](v2/03-website.md)) replacing
  `/static/public/...`-style URLs, which leaked the on-disk directory
  layout into every link a visitor could see or share.
- **Migrated v1's test patient data** into a Pro practitioner's vault by
  hand (one-off script, not a route) so existing POC demo data stayed
  visible after the cutover instead of being silently orphaned.

## v2 — 2026-08-13

Scope expanded from a single-practitioner PoC to the full multi-tenant
product: a public marketing/directory website, an admin portal, a
practitioner portal (basic + pro plans), and a client portal.

**Why:** the PoC proved grounded, cited RAG answers work. The next step is
the product around it — practitioner acquisition (public directory site),
operator tooling (admin), and self-serve practitioner accounts with paid
tiers (Stripe), sized for 10–20 practitioners.

**What's new vs. v1:**
- Public website: about page, practitioner signup, practitioner directory
  (photo, description, specialties, languages, years of experience,
  consultation price — modeled partly on vibly.io's directory), coach detail
  page with a contact form for a client to request an initial call.
- Multi-tenant practitioner accounts on two plans:
  - **Basic** — public profile only.
  - **Pro** — RAG access with the practitioner's own Anthropic API key, a
    separate patient DB, and the ability to create client accounts. No
    library access (library stays admin-curated).
- Admin portal: practitioner CRUD + plan management, library/RAG management
  (all four v1 LLM roles, not a trimmed subset), questionnaire admin, website
  statistics (traffic, per-practitioner profile views, contact forms sent),
  and per-practitioner patient counts.
- Client portal: intake questionnaire, file upload (lab PDFs etc.), and
  wearable integration (Oura, Whoop, Garmin).
- Stripe billing for the practitioner Pro plan. No client-side payments yet.

**Explicitly still out of scope:** mobile app, employer portal, telehealth
video, booking/scheduling, client-to-practitioner payments.

**Superseded:** [v1](v1/README.md) is frozen as-is; nothing in it was edited.

## v1 — Phase 1 PoC

Initial cut. See [v1/README.md](v1/README.md). Not tracked here in detail —
this changelog starts at the v1 → v2 transition.
