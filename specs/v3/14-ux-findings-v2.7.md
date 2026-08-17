# 14 · UX findings — v2.7 candidate

Produced by a UX audit of the live deployment
(`https://telehealth.devshorepartners.id`) and the codebase, acting as PM
(user flows, friction, unmet promises, cross-page consistency) — on
2026-08-14, on top of [13 · Known issues](13-known-issues.md) (v2.6
backlog; all Critical/High findings from that review already fixed
same-day). This pass walked the golden path the product is built
around — a practitioner reviewing a new client's intake before a
consult — plus the client and admin portals and the public site, and
recorded net-new findings only; it does not re-list anything already
covered by 13. Grouped by portal, each finding gives severity, the
problem as observed against the shipped code, and a fix direction
(layout/flow only — no visual-style changes were audited or proposed).

**Status: all 20 findings resolved as of v2.12** (see
[CHANGELOG](../CHANGELOG.md) v2.7–v2.12 for what shipped and when — each
finding's entry above names the version that fixed it). This document
originally recorded a spec-only backlog; it's kept as the historical
record of what the audit found and how each item was actually addressed,
not as an open todo list anymore.

---

## Practitioner portal

### P1 — Critical: "Start consultation" on a client's page doesn't actually start a consultation with that client

`static/practitioner/client-detail.html` renders a "Start consultation"
button (`#cl-consult-link`) that is a plain `<a href="/practitioner/consult">`.
`static/practitioner/consult.html` never reads a query string or any
other context on load — `selectedClient` starts `null` and the
practitioner must find and click the same client again in the Consult
page's client list. The button visually promises "jump into a consult
with this person" and instead just re-opens the generic Consult picker,
one extra click removed from where they already were. This directly
undermines the golden path this audit was asked to walk (review intake →
consult).

**Fix direction:** have the link carry the client id (e.g.
`/practitioner/consult?client=<id>`) and have `consult.html` read that
param on load and call the existing `selectClient()` with it, so the
button does what it says.

### P2 — High: Consult and the client-detail page don't cross-link, so a practitioner loses their place mid-task

While chatting with a client in Consult, there is no link back to that
client's Intake review or Consultations & reports (the page only shows
"Ask Clinic about {name}", no href). Conversely, `client-detail.html`'s
session rows let a practitioner view/expand a past conversation and its
documents, but there's no way from there to continue that specific
conversation — only from Consult, which (per P1) can't be pointed at a
specific session either. The two newest pages about the same client
don't know about each other.

**Fix direction:** add a persistent link/breadcrumb from Consult's
ask-panel to `/practitioner/clients/{id}` (and back), and pass a
`session_id` through so "Resume" on an in-progress session actually
reopens that conversation in Consult instead of only flipping its
status.

### P3 — High: "Resume" on an in-progress consultation doesn't resume anything

In `client-detail.html`, `sessionRow()` offers a "Resume" button on any
non-`done` session, but its handler only PATCHes the session's `status`
field back and forth — it never opens Consult against that session.
Combined with P1/P2, there is currently no UI path that continues a
specific prior session's conversation; every visit to Consult before a
session is marked "done" silently starts a brand-new session for that
client (`POST /api/me/consult` creates a new session whenever
`session_id` is falsy — `app/main.py` line ~862), so "in progress"
sessions can pile up unreachable.

**Fix direction:** "Resume" should navigate to Consult with that
session's id (once P1's param exists) rather than only toggling status.

### P4 — Medium: Consult's client list gives no signal about intake completeness

The golden path this audit names explicitly ("practitioner reviewing a
new client's intake before a consult") requires leaving Consult, going
to Clients, opening the client, checking Intake review, then coming
back. Consult's own client list (`#client-list` in `consult.html`)
shows only name/email/avatar — no chip for "intake submitted" or "no
response yet" — so a practitioner can't tell from the picker whether a
consult is well-informed or premature.

**Fix direction:** add a small chip/indicator on each client row in
Consult's sidebar (e.g. "intake ✓" / "no intake yet") sourced from the
same data `client-detail.html` already fetches, so the check can happen
without leaving the page.

### P5 — High: Editing a client's profile record has three separate, uncoordinated document surfaces with no combined view

On `client-detail.html`, each consultation session has its own Clinician
note and Client report (draft/final), and there's a separate "Reports &
documents" side panel listing all documents across sessions — but that
side panel is just a flat, unclickable list (`documentRow()` renders
plain text, no click handler to jump to the source session). A
practitioner scanning "Reports & documents" to find a specific final
report has no way to open it from there; they must scroll the session
list and expand the matching session manually.

**Fix direction:** make each row in "Reports & documents" clickable,
expanding/scrolling to its parent session in the left column (or open
the session's detail inline from the click).

### P6 — Medium: Two competing document idioms coexist per session with no visual distinction of purpose

Each session shows a "Clinician note" and a "Client report" side by
side, both draft/final, both plain textareas with the same
Save/Mark-final buttons. Nothing in the layout signals that one of these
(Client report) is meant to eventually be seen by the client and the
other (Clinician note) is internal-only — a practitioner skimming
quickly could type sensitive internal reasoning into the wrong box. This
is exactly the kind of "could mislead about what an action will do" risk
the audit calls out.

**Fix direction:** give the two document blocks a structural
separator/label reinforcing audience (e.g. group under two subheadings
"Internal" / "Shared with client" rather than two same-weight
side-by-side fields) — layout only, not a color change.

### P7 — Medium: Profile page's Anthropic API key panel is easy to miss on first Pro upgrade

`profile.html` puts the API key panel as a second, separate card below
the main profile form. The practitioner's landing page is now Consult
(not Profile), so a newly-upgraded Pro practitioner who goes straight to
Consult and asks a question gets the 400 error path (already fixed to
link to `/practitioner/profile`, [13 · C3](13-known-issues.md)) rather
than being guided to set the key proactively. Nothing on Consult (or
Upgrade's post-checkout state) prompts for the key before the first
failed question.

**Fix direction:** on first landing after upgrade (or whenever
`has_anthropic_key` is false and plan is Pro), show a one-time
banner/empty-state on Consult itself pointing at the profile key panel,
instead of only reacting after a failed question.

### P8 — RESOLVED (fixed same day, alongside the addendum's nav changes): Upgrade page's "Already on Pro" copy referenced Clients while the practitioner's default landing was Consult

`upgrade.html`'s post-upgrade message said "Head to Clients to get
started" — but the actual default landing page (per this session's
context) was Consult, not Clients. Fixed by pointing the copy at Consult
in the same edit that hid the Upgrade nav link once already on Pro (see
addendum #3). Superseded again by the v2.8 dashboard round, where the
default landing became `/practitioner/dashboard` — the copy should be
re-checked against that if dashboards are audited next.

~~Fix direction: point the copy at Consult (or Clients, whichever is
the intended first Pro action) to match the current landing-page
decision.~~

### P9 — Low: "Add a client" is tucked inside a collapsed `<details>` on a page with no other content

`clients.html` puts the entire add-client form behind a
`<summary>Add a client</summary>` disclosure below an otherwise empty
list on first use. For a brand-new Pro practitioner with zero clients,
the empty state message ("Add one below…") points at a collapsed
section rather than an already-open form — an extra click for the very
first, most common action on this page.

**Fix direction:** default the disclosure open when the client list is
empty.

---

## Admin portal

### A1 — High: The questionnaire builder's single-active-questionnaire model is a destructive trap with no warning at the point of action

Per [04 · Admin portal §3](04-admin-portal.md#3-questionnaire-admin), only
one questionnaire is active at a time, and saving any edit (`b-save`)
makes that edited lineage the sole active one — deactivating whichever
different questionnaire was previously active. `admin/questionnaires.html`'s
hint text explaining this appears once, above the list, and nowhere near
the "Save as new version" or "Edit (new version)" buttons. An admin who
has, say, an "Intake" and an unrelated "Post-op" questionnaire, and
edits the Post-op one just to fix a typo, silently swaps the
client-facing active questionnaire without any confirmation.

**Fix direction:** show which questionnaire is currently active more
prominently (e.g. a dedicated "Currently active" section separate from
the flat version list), and add a confirmation step on Save when the
edited questionnaire is not already the active one ("Saving will make
this the active questionnaire, replacing X — continue?").

### A2 — Medium: Editing an old, already-superseded version can silently branch from stale content

Clicking "Edit (new version)" on *any* row in the list — including an
inactive, older lineage — opens the builder pre-filled from that row's
content and, on save, creates `version + 1` of that specific lineage and
makes it active. There's no indication in the list which questionnaire
is the "current" one an admin probably meant to edit versus a historical
one they clicked by mistake (all rows look the same weight, only a
small `active`/`inactive` chip differs).

**Fix direction:** visually separate the active questionnaire from the
rest of the list (e.g. pin it above a "Previous versions" subsection) so
the default click target is unambiguous.

### A3 — Medium: No breadcrumb on the primary admin page (`/admin`), inconsistent with every other admin/practitioner/client page

`static/index.html` (the knowledge-admin dashboard, served at `/admin`)
has an `app-topbar` containing only the account menu — no
`<nav class="breadcrumbs">` — while `admin/users.html` and
`admin/questionnaires.html` both show "Admin / Users" and
"Admin / Questionnaires" breadcrumbs linking back to `/admin`, per the
shared navigation conventions in
[03 · Website](03-website.md#shared-navigation-conventions). Since
`/admin` is the root of that breadcrumb chain, its own topbar reads as
unfinished/inconsistent next to its sibling pages.

**Fix direction:** add a minimal breadcrumb to `/admin` for consistency
(even just "Admin", non-linking) so all three admin pages share the same
topbar shape.

### A4 — Low: New-credentials panel and site-stats panel compete for the same page real estate with no persistent placement

`admin/users.html` shows the "Account created" credentials panel (added
in [13 · H4](13-known-issues.md)) at the very top of `<main>`, above
Site statistics ([13 · H5](13-known-issues.md)) — appropriate
immediately after creating an account, but it stays there occupying
prime position until manually dismissed, pushing Site statistics and the
Practitioners list down every time an admin adds someone. On a page an
admin may revisit often, this reordering-by-side-effect is a small but
repeated disorientation.

**Fix direction:** keep the credentials panel in a fixed slot (e.g.
anchored near the create form itself, not page-top) so the rest of the
page doesn't reflow around it.

---

## Client portal

### C1 — RESOLVED: A client's questionnaire answers could never display in the practitioner's Intake review — key mismatch between submit and read paths

Fixed live the same day this was found, before any real client data was
affected — no client had submitted against the new Intake review feature
yet. `client/questionnaire.html` built its submission as
`answers[q.prompt] = readAnswer(q, i)` — keyed by the question's
**prompt text**. `practitioner/client-detail.html`'s `loadIntake()` reads
them back as `answers[q.id]` — keyed by the question's **database id**.
Fixed by changing the submit handler to key by `q.id`, matching the read
path.

### C2 — Low: Wearables connect flow leaves the browser via a full-page redirect with no loading/transition state

`client/wearables.html`'s connect handler does `location.href = r.url`
immediately on success with no interstitial ("Redirecting to Oura…") —
on a slow connection the button just goes inert-looking (disabled, no
spinner) for however long the request takes before navigation actually
happens.

**Fix direction:** show a brief "Redirecting…" state on the button
between the API response and the navigation, matching the
`.working`/`.spin` pattern already used elsewhere (e.g. Consult's
"Clinic is thinking").

### C3 — Low: Questionnaire's empty/no-active-questionnaire state offers no path to Files or Wearables

If `GET /api/me/questionnaire` returns null (no active questionnaire),
`questionnaire.html` shows "Nothing to fill in right now — check back
later" with no links, unlike the post-submit success state which does
link to Files and Wearables ([06 · Client portal](06-client-portal.md#initial-questionnaire)).
A client landing here first (their default landing page) with no active
questionnaire has no next action suggested at all.

**Fix direction:** give the no-active-questionnaire empty state the same
"next steps" links (Files, Wearables) the post-submit state already has.

---

## Public site

### S1 — High: Logged-in users still see "Sign up" / "Log in" in the sidebar on every public page

`static/public/*.html` sidebars (directory, coach, about, signup, login)
are static markup with no session check — `shared.js` has no logic
anywhere to hide/replace "Sign up"/"Log in" for an authenticated
visitor. A practitioner or client who is already logged in and browses
back to `/directory` or `/about` (e.g. via the browser back button, or a
shared link) still sees "Sign up" and "Log in" as if signed out, with no
visible link back to their own portal from these pages (only the
Account/logout path exists once they're already inside a portal).
`login.html` alone auto-redirects an authenticated visitor away; no
other public page does.

**Fix direction:** on public pages, check `currentSession()` (already
available via `shared.js`) and swap "Sign up"/"Log in" for a single "Go
to my dashboard" / portal link when a session exists, matching what
`login.html` already does.

### S2 — High: `/account` is a dead end for every logged-in role — no way back to your own portal

`static/public/account.html`'s sidebar has a brand-link (logo) but **no
`<nav class="sidebar-nav">` at all** — every other authenticated page
has 3–5 portal links here. Its topbar likewise has only a Log-out
button, no breadcrumb (`/account` is itself the shared-navigation
convention's documented exception for the user-menu pattern, per
[03 · Website](03-website.md#shared-navigation-conventions), but that
exception was never meant to also drop the sidebar nav). A
practitioner/client/admin who opens Account from the user-menu loses all
of their portal navigation; the only way back is the browser's back
button (or logging out). Worse, the logo/brand-link on this page points
to `/directory` — the public marketing site — breaking the pattern every
other authenticated page uses (logo → your own portal home, per
[03](03-website.md#shared-navigation-conventions)). A user unfamiliar
with the browser back button could reasonably believe they've been
logged out of their portal.

**Fix direction:** give `account.html` a role-aware sidebar nav (reuse
the same 1–2 links the calling portal would show, or at minimum a single
"Back to my portal" link derived from the session's role) and point its
brand-link at the role's home page instead of `/directory`.

### S3 — Medium: Sidebar on narrow viewports (≤900px) crowds brand, tagline, and 3–5 nav links into one horizontally-scrolling row with no scroll affordance

Per `static/style.css`'s `@media (max-width: 900px)` block, `.sidebar`
switches to `flex-direction: row` with `overflow-x: auto`, keeping the
full brand block (logo + "Clinic" + subtitle + "Phase 2 POC" tag) inline
with the nav links in the same scrollable strip. There's no fade/arrow/
indicator that more items exist off-screen, and on the public site's
5-link sidebar or practitioner's 5-link sidebar this makes the
first-visible nav item(s) easy to miss, especially since the brand block
itself eats significant width before any nav link is visible.

**Fix direction:** on narrow viewports, drop the tagline/tag pill from
the row (keep just the mark) so nav links surface sooner, and/or add a
lightweight edge-fade to signal horizontal scroll is available —
layout/positioning changes only.

### S4 — Low: `practitioner-signup-thanks.html` promises Upgrade is reachable "from your profile page," but Upgrade is its own sidebar link, not on Profile

Minor copy/navigation mismatch: the thanks page says upgrading to Pro is
"a separate step available from your profile page," but in the actual
sidebar (`profile.html`), Upgrade is a distinct top-level nav item, not
something surfaced on the Profile screen itself
([05 · Practitioner portal](05-practitioner-portal.md#upgrading-basic--pro)).
A newly-approved practitioner following this copy literally would look
at Profile and not find it there.

**Fix direction:** either add an Upgrade CTA/link on the Profile page
itself (matching the copy), or update the copy to say "from the Upgrade
page in your sidebar."

---

## Cross-portal consistency notes

- **Tabs pattern is new and inconsistent with existing patterns.**
  `client-detail.html` introduces the app's first tab control ("Intake
  review" / "Consultations & reports") using plain `.btn.ghost` buttons
  toggled with a custom `.on` class and a bare `role="tablist"` wrapper —
  no `role="tab"`/`aria-selected` on the buttons, no `role="tabpanel"` on
  the panels. Every other multi-view page in the app (admin's
  numbered-step panels, `.pane.on` panels) uses a different idiom
  entirely. Low severity, but worth aligning if a second tabbed page is
  ever added.
- **Status chip color/weight is consistent** across draft/final,
  active/inactive, pending/approved/etc. (`.chip` / `.chip.warn`) — no
  issue found here, called out only because the audit asked to check it.
- **Empty states are consistently helpful** (`empty()` helper in
  `shared.js` used everywhere, always names a next action) — one gap
  found and listed above (C3).

---

## Summary

| ID | Portal | Severity | Status |
|---|---|---|---|
| P1 | Practitioner | Critical | RESOLVED (fixed v2.9) |
| P2 | Practitioner | High | RESOLVED (fixed v2.9) |
| P3 | Practitioner | High | RESOLVED (fixed v2.9) |
| P4 | Practitioner | Medium | RESOLVED (fixed v2.9 — intake shown in the overview panel, not a list chip) |
| P5 | Practitioner | High | RESOLVED (fixed v2.10) |
| P6 | Practitioner | Medium | RESOLVED (fixed v2.10) |
| P7 | Practitioner | Medium | RESOLVED (fixed v2.11) |
| P8 | Practitioner | Low | RESOLVED (fixed same day) |
| P9 | Practitioner | Low | RESOLVED (fixed v2.11) |
| A1 | Admin | High | RESOLVED (fixed v2.12) |
| A2 | Admin | Medium | RESOLVED (fixed v2.12) |
| A3 | Admin | Medium | RESOLVED (fixed v2.12) |
| A4 | Admin | Low | RESOLVED (fixed v2.12) |
| C1 | Client | — | RESOLVED (fixed live same-day) |
| C2 | Client | Low | RESOLVED (fixed v2.12) |
| C3 | Client | Low | RESOLVED (fixed v2.12) |
| S1 | Public | High | RESOLVED (fixed v2.12) |
| S2 | Public | High | RESOLVED (fixed v2.12) |
| S3 | Public | Medium | RESOLVED (fixed v2.12) |
| S4 | Public | Low | RESOLVED (fixed v2.12) |

1 Critical, 6 High, 6 Medium, 6 Low findings open; 1 (C1) already
resolved. Build order/priority across these is a separate, later
decision — not made here.

---

## Addendum — practitioner sidebar simplification (decided and built same day)

Unlike the findings above, these five items were direct product decisions
(not audit findings) made and shipped the same day this document was
written, ahead of any prioritization of the findings above:

1. **Profile moved into the account dropdown.** It was a sidebar link
   duplicating what the user-menu (Account/Log out) already covers
   conceptually — a practitioner's own settings. Now `/practitioner/profile`
   is reached via the same dropdown as Account/Log out, not a separate
   top-level nav item.
2. **Consult is the first sidebar link**, reflecting it being the
   practitioner's actual default landing page (changed earlier this same
   document's v2.7 entry) — the nav order now matches the entry point.
3. **Upgrade hides once a practitioner is already on Pro.** Showing an
   "upgrade" link to someone who already upgraded was dead weight; the
   sidebar now fetches `GET /api/me/profile` on load and hides the link
   when `plan === 'pro'`.
4. **Clients removed as a standalone sidebar item.** Consult's own client
   list already serves as the practitioner's client picker; keeping a
   second, separately-navigated "Clients" page for the same underlying list
   was redundant navigation for one concept. `/practitioner/clients` still
   exists (a client's intake review and consultation history live there,
   linked to from `/practitioner/clients/{id}`), but a practitioner reaches
   an individual client's detail page via a link on that client's row in
   Consult's picker, not via a dedicated nav entry.
5. **Knowledge base surfaced to practitioners, with a per-practitioner-only
   weight.** Practitioners can now browse the shared library (read-only —
   title, kind, origin, grade, topics, same data admin's dashboard shows)
   and set their own personal weight override per source. This override is
   private to that practitioner: it is stored in their own vault
   (`source_weights` table), never touches the admin-set `grade` on the
   shared Neo4j `Source` node, and is invisible to every other practitioner
   and to admin. It affects only that practitioner's own `POST /api/me/consult`
   calls — after `knowledge.catalogue()` returns the admin-graded list, that
   practitioner's overrides are applied in-memory to `grade` before the
   Librarian/Specialist see it, re-filtering against their chosen minimum
   grade. Deep-traversal hop expansion (`knowledge.traverse()`) still reads
   the shared admin grade directly — the override's effect is scoped to
   which sources are *offered* to the Librarian, not the full expansion
   graph, a deliberate scope-down rather than rewriting `traverse()`'s own
   grade filtering to be practitioner-aware.
