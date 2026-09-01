# 17 · Full-app redesign — PM + UX walkthrough

Requested directly ("go through all the features, propose redesign for
better user flow and experience, make it simple and interesting") — a
full-app pass, not a single-page one like
[16 · `/admin/users` redesign](16-users-page-redesign.md). Two personas, one
walkthrough: a **PM** asking whether each screen serves the user's actual
goal, whether the flow is coherent, whether anything is redundant or
missing; a **UX designer** asking whether each screen is legible,
consistent, and feels "simple and a little delightful, not sterile." Same
audit format as [14 · UX findings v2.7](14-ux-findings-v2.7.md) — severity,
problem as observed against the shipped code, fix direction — grouped by
portal, plus a cross-cutting section. Findings are prefixed by portal
(`PUB`/`PRAC`/`ADM`/`CLI`) to avoid collision with 14's `P`/`A`/`C`/`S`
numbering, since both documents are read side by side.

**Status: implemented**, with three scope decisions made during the build
that this document's original proposal didn't call out:

- **PRAC2/X2** — `client-detail.html`'s tab toggle got the missing
  `role="tab"`/`aria-selected`/`role="tabpanel"` wiring, but was **not**
  migrated to `md-tabs`; that page has never had the MD3 build pipeline
  (no `dist/` script, no `theme.css`/`components.css` links), and pulling
  it in for one Low-severity consistency fix was judged disproportionate.
  `admin/users.html`'s tabs *did* move to real `md-tabs`/`md-primary-tab`,
  since that page already has the pipeline. One idiom reduced to two
  cases instead of one — a partial win, not the full standardization
  proposed.
- **`practitioner/clients.html`'s datatable** uses Sessions/Records/Added
  as its three data columns, not "Last session date" as this document's
  X3 section suggested — `vault.list_clients()` returns session/entry
  *counts*, not a last-session timestamp; adding that column would need a
  backend query change, which wasn't in scope for this pass.
- **A real bug, found and fixed along the way, not in the original
  findings**: `admin/users.html`'s `load()` called `loadPractitioners()`
  (which reads `$('p-filter').value` synchronously to build its query
  string) *before* applying the `?status=`/`?plan=` deep-link params to
  the filter controls — so the "Review"/stat-row links this document's
  ADM2 and [16](16-users-page-redesign.md) both rely on never actually
  filtered on first load. Fixed by reordering.

`CLI2` (file delete) and the JS-grid-library alternative remain
unimplemented, as originally flagged — both were marked out of scope in
this document from the start, not skipped during the build.

**Scope note (unchanged from the original spec-only version):** every
finding below was checked against the shipped markup/JS as of the
original audit session — not against [13](13-known-issues.md) or
[14](14-ux-findings-v2.7.md)'s already-fixed items, which are not
re-litigated here.

**What was walked:** `static/public/*.html` (about, account, client-signup,
coach, directory, login, practitioner-signup(-thanks)), `static/index.html`
(admin's knowledge dashboard), `static/admin/*.html` (dashboard, users,
questionnaires), `static/practitioner/*.html` (dashboard, clients,
client-detail, consult, contacts, knowledge, profile, upgrade),
`static/client/*.html` (dashboard, files, questionnaire, wearables),
`static/style.css`, `static/shared.js`, against
[01](01-overview.md)/[03](03-website.md)/[04](04-admin-portal.md)/
[05](05-practitioner-portal.md)/[06](06-client-portal.md)/
[09](09-payments.md)/[15](15-design-system.md).

**Headline finding, stated up front:** this app already went through two
real redesign passes ([13](13-known-issues.md), [14](14-ux-findings-v2.7.md),
plus the [16](16-users-page-redesign.md) rebuild and the addendum's sidebar
simplification) and it shows — the practitioner golden path (review intake
→ consult) is genuinely tight now, empty states are consistently helpful,
and the glass/gradient/botanical visual language in
[15](15-design-system.md) is distinctive rather than generic-SaaS. What's
left is narrower than a previous pass would suggest: two page shells that
never finished converging, a component gap (tables) the app has been
quietly working around with a card-list pattern that doesn't fit every
list, and a public/marketing surface that's functionally correct but has
no personality compared to the portals behind login.

---

## Public / Website

### PUB1 — High: two incompatible page shells coexist on the public site

`static/public/about.html`, `directory.html`, `coach.html`, and
`account.html` use the floating red-glass `.sidebar` + `.app-shell` layout
([15 §Glass finish](15-design-system.md#glass-finish)). But
`static/public/login.html`, `client-signup.html`, `practitioner-signup.html`,
and `practitioner-signup-thanks.html` still use the older flat
`<header class="topbar">` with an inline `.topbar-inner` nav row — the shell
every page used before the sidebar redesign landed. These four pages are
exactly the ones a brand-new visitor sees first. A visitor who clicks
"Join as a practitioner" from `/about` (sidebar shell, red gradient nav)
lands on `/join` (flat white topbar, no sidebar) — the product visually
changes underneath them mid-flow, then changes back on
`practitioner-signup-thanks.html`, then again once they log in and land in
a portal that uses the sidebar shell again. Grepping confirms the split is
total, not partial: every file under `static/public/` either has
`<div class="app-shell">…<aside class="sidebar">` or `<header class="topbar">`,
never both, never a third pattern.

**Fix direction:** migrate `login.html`, `client-signup.html`,
`practitioner-signup.html`, and `practitioner-signup-thanks.html` to the
`.app-shell`/`.sidebar`/`.app-topbar` markup already used by their sibling
public pages — same nav links (`About`/`Find a practitioner`/`Join as a
practitioner`/`Sign up`/`Log in`, swapped via `data-auth-link` exactly as
`about.html` already does), same brand-link target. No new CSS needed —
`.sidebar` and `.app-topbar` are already themed and already handle the
`data-auth-link` swap via `shared.js`'s `adaptPublicAuthLinks()`, which
these four pages already call.

### PUB2 — Medium: coach.html stacks two same-weight CTAs with no framing for which to use

`static/public/coach.html` renders "Get in touch" (`#contact-panel`, a
name/email/message form) and, immediately below it when the practitioner is
Pro, "Ready to work together?" (`#signup-panel`, a single "Sign up as their
client" button) as two visually equal `.card-panel` blocks. Nothing on the
page tells a visitor which one is the right first move, or that they're
different kinds of commitment — one is a lead-capture message (no account,
["Send a message... doesn't book a slot"](03-website.md#coach-detail-page)),
the other is creating a full account and starting intake. A visitor who
wants to "just ask a quick question" and one who's ready to commit see the
identical layout with no signal to tell them apart.

**Fix direction:** give the two panels distinct weight and framing —
promote "Sign up as their client" to the primary action (it's the
higher-intent, product-relevant one) with copy like "Ready to start? Sign
up and complete your intake," and demote the contact form to a secondary,
lower-visual-weight block with copy like "Have a question first? Send a
message" — ordering and hierarchy only, both stay on the page.

### PUB3 — Medium: the directory has no free-text search, only two dropdown filters

`static/public/directory.html`'s `.filter-row` has `#f-specialty` and
`#f-language` `<select>`s and nothing else — no `<input class="search">`
despite `style.css` already defining `.search` (a text input with a
built-in magnifying-glass icon, used by `static/index.html`'s library
search) and despite `admin/users.html` establishing exactly this
search-alongside-filter pattern for its own list
([16](16-users-page-redesign.md)). A visitor who knows a practitioner's
name has no way to jump straight to them; they have to guess which
specialty tag that practitioner might be filed under.

**Fix direction:** add a `.search` input beside the two filter dropdowns,
client-side over the already-fetched `all` array (matches name and bio,
same "fine at this scale" reasoning already applied elsewhere) — no new
endpoint.

### PUB4 — Low: practitioner-signup.html is an unbroken 8-field form

`static/public/practitioner-signup.html` puts name, email, password, bio,
specialties, languages, years, price, and a photo picker in one
undifferentiated column with no section breaks — the practitioner's very
first interaction with the product is a wall of fields, no different in
presentation from any of them being more or less important.

**Fix direction:** group into two visual sections with a `.vine` divider
(the leaf-and-hairline divider already used elsewhere, e.g.
`coach.html`/`about.html`) — "Account" (name, email, password) then
"Your public profile" (bio, specialties, languages, years, price, photo) —
layout grouping only, still one page, one submit.

### PUB5 — Low: the directory and About page have no visual identity beyond the card grid

`static/public/directory.html` opens straight into the filter row and card
grid with no hero copy, no value proposition, nothing that frames "browse
and discover a practitioner" as different from "fill in a form" the way
every other page in the app opens with at least a `.ph` header explaining
what the panel is for. `about.html` is a single card of paragraph text. For
a product whose entire public-facing job is to get a visitor to pick a
practitioner, the discovery surface is the least considered page in the
product visually.

**Fix direction:** see [Visual/interaction ideas](#visual-interaction-ideas)
below — a short intro line above the filter row, reusing the existing
`.hint`/`.vine` idiom, not a new design language.

---

## Practitioner portal

### PRAC1 — Medium: "Add a client" is still a native `<details>` disclosure, unlike admin's equivalent form

`static/practitioner/clients.html`'s `#cl-add-details` is a plain HTML
`<details><summary>Add a client</summary>` wrapping the create-client
fields, sitting inline under the client list at all times (open by default
only when the list is empty, per the already-fixed
[14 §P9](14-ux-findings-v2.7.md#p9--low-add-a-client-is-tucked-inside-a-collapsed-details-on-a-page-with-no-other-content)).
This is the exact "creating an account and browsing the list are
permanently the same view" problem
[16 §U4](16-users-page-redesign.md#u4--creating-an-account-and-browsing-the-list-are-permanently-the-same-view)
already diagnosed and fixed for `admin/users.html` by moving creation into
an `md-dialog` — but the fix was never carried over to the practitioner's
own, structurally identical client-roster page. A practitioner with 15
clients scrolls past a permanently-present create form to reach client #15,
same as the admin problem `md-dialog` already solved once.

**Fix direction:** same pattern as `admin/users.html`'s `#np-dialog` — move
the two fields (name, email) into an `md-dialog` opened by a
"+ Add client" button next to the panel header, closing on success with the
new row appearing in the list. Smaller lift than `admin/users.html`'s
version since there's no credentials-reveal step (a Pro-created client has
no password yet — they set one completing their own signup, per
[06](06-client-portal.md)).

### PRAC2 — Low: three different hand-rolled tab idioms now exist, none of them `md-tabs`

`static/practitioner/client-detail.html`'s "Intake review"/"Consultations &
reports" toggle uses plain `.btn.ghost` buttons with a bare
`role="tablist"` wrapper — no `role="tab"`, no `aria-selected` on the
buttons, no `role="tabpanel"` on the panels — already flagged as a low-
severity cross-cutting note in
[14](14-ux-findings-v2.7.md#cross-portal-consistency-notes) and still true
today. Since that note was written, `admin/users.html` shipped a *second*,
differently-styled tab pattern (`.tab-bar`/`.tab-btn`,
[16](16-users-page-redesign.md)) with correct `role="tab"`/`aria-selected`
wiring but its own bespoke CSS. Two tab idioms now coexist, neither of them
the MD3 `md-tabs`/`md-primary-tab` component this project has had available
since [15](15-design-system.md) shipped.

**Fix direction:** standardize both on `md-tabs`/`md-primary-tab` — it's a
strict upgrade over both current patterns (correct ARIA out of the box,
ripple/indicator built in) and collapses two maintained idioms into the one
the design system is supposed to be built from.

### PRAC3 — Low: knowledge.html gives no at-a-glance count of how many sources are personalized

`static/practitioner/knowledge.html` shows every library source as its own
full-width `.card-panel` with a per-row "personalized" / "matches admin
grade" chip (`data-status`), but the page header (`#kb-count`) only shows
the total source count, not how many carry a personal override. A
practitioner checking "what have I actually customized" has to scroll the
full list reading chips one at a time.

**Fix direction:** add a second, small count next to `#kb-count` — "3
personalized" — computed client-side from the already-fetched
`/me/knowledge` response, no new endpoint.

---

## Admin portal

*(`/admin/users` itself is out of scope per the task brief — already
redesigned in [16](16-users-page-redesign.md). Findings below are about
`/admin/dashboard` and `/admin/questionnaires`, and about how they connect
to `/admin/users`.)*

### ADM1 — Medium: two lists that will outgrow "a handful of rows" have no sort

`static/admin/questionnaires.html`'s "Previous versions" list
(`questionnaireRow()`) and `static/admin/dashboard.html`'s "Pending
applications" panel (`pendingRow()`) both render as flat, unordered
`<ul class="rows">` — no way to sort the questionnaire history by version
or date, no way to sort pending applications by submission date. Small
today (few historical questionnaire versions, a handful of pending
practitioners at once), but this is the identical shape of problem
[16 §U5](16-users-page-redesign.md#u5--no-way-to-find-one-practitioner-by-name)
already named for the practitioner list before it grew — "tolerable at
scale, stops being tolerable once the roster grows past a screenful."

**Fix direction:** see [cross-cutting §X3](#x3--component-need-most-data-lists-should-be-real-data-tables-not-stacked-card-rows)
below.

### ADM2 — Low: dashboard's stat numbers don't link to the filtered list that explains them

`static/admin/dashboard.html`'s `#site-stats` table shows "Total
practitioners" and "Pro plan" as bare numbers in a `.tbl` — not links.
`admin/users.html` already supports `?status=` deep-linking from the
"Pending applications" `Review` button
([16](16-users-page-redesign.md#redesigned-page)), but nothing extends that
same pattern to "Total practitioners" (→ `/admin/users` unfiltered) or "Pro
plan" (→ `/admin/users?plan=pro`, would need a plan filter added to
`users.html`, currently status-only). An admin who sees "Pro plan: 4" and
wants to see which four has to navigate to Users and can't get there in one
click from the number that prompted the question.

**Fix direction:** make each stat row a link into the equivalent
`admin/users.html` view — "Total practitioners" → `/admin/users`, "Pro
plan" → `/admin/users?tab=practitioners&plan=pro` (needs a small plan
filter added to `users.html` alongside the existing status filter — a
config addition to an already-client-side-filtered list, not a new
endpoint).

---

## Client portal

### CLI1 — High: the client's documented first-landing page uses the old page shell

[06 · Client portal](06-client-portal.md#initial-questionnaire) is explicit
that "on first login... the client completes the... active questionnaire"
— `static/client/questionnaire.html` is the client's very first
authenticated screen. It uses the legacy flat `<header class="topbar">`
shell (inline nav row: Dashboard/Questionnaire/Files/Wearables, all as
`.btn.ghost.sm` buttons in the topbar) while every *other* client page
(`dashboard.html`, `files.html`, `wearables.html`) uses the floating
`.sidebar`/`.app-shell` layout. A brand-new client's first authenticated
impression of the product is structurally different from the rest of their
own portal one click later — same root cause as [PUB1](#pub1--high-two-incompatible-page-shells-coexist-on-the-public-site),
worse in effect because this is a first-run page for a role, not just the
public site.

**Fix direction:** migrate `client/questionnaire.html` to `.app-shell`/
`.sidebar`/`.app-topbar`, matching `dashboard.html`/`files.html`/
`wearables.html` exactly — same nav links, same breadcrumb pattern already
present in the flat version (`<nav class="breadcrumbs">` already exists on
this page, just outside the sidebar shell instead of inside `.app-topbar`).

### CLI2 — Low: uploaded files show name and date only

`static/client/files.html`'s `loadFiles()` renders `f.original_name` and
`f.uploaded_at` and nothing else — no file type or size, no way to remove a
file uploaded by mistake (e.g., the wrong PDF). A client who uploads the
wrong lab report has no self-service way to fix it; they'd need their
practitioner or an admin to intervene through a code path that doesn't
exist yet.

**Fix direction (partially backend-dependent):** showing file type (already
in the client-facing `GET /api/me/files` shape, since size/type would
normally accompany `original_name`) is a display-only fix. A client-side
**delete** action would need a new endpoint (`DELETE /api/me/files/{id}`)
— flagging that specific piece as **requires new backend work**, not
bundled into the display fix.

---

## Cross-cutting

### X1 — High: nav shell inconsistency spans two portals, not one

[PUB1](#pub1--high-two-incompatible-page-shells-coexist-on-the-public-site)
and [CLI1](#cli1--high-the-clients-documented-first-landing-page-uses-the-old-page-shell)
share one root cause: the sidebar/topbar redesign
([15](15-design-system.md), and the `CHANGELOG.md` v2.4-v2.7 nav polish it
references) was never applied to every page — five pages across two
portals (`public/login.html`, `public/client-signup.html`,
`public/practitioner-signup.html`, `public/practitioner-signup-thanks.html`,
`client/questionnaire.html`) still carry the pre-redesign flat `.topbar`
markup. All five are first-run or first-landing pages for some role — the
exact place visual consistency matters most, and the exact place it's
currently missing. Grouped here because the fix is the same mechanical
migration in every case (swap the shell markup, reuse the page's own
already-correct nav links and `data-auth-link`/breadcrumb data) and because
a single pass covering both portals is more efficient than filing it twice.

### X2 — Medium: three tab idioms, one MD3 component that should replace all of them

Covered in detail at [PRAC2](#prac2--low-three-different-hand-rolled-tab-idioms-now-exist-none-of-them-md-tabs).
Listed again here because it's a component-need finding, not a
single-page one: `md-tabs`/`md-primary-tab` should be the one tab pattern
this app has, replacing both `client-detail.html`'s ARIA-incomplete toggle
and `admin/users.html`'s custom `.tab-bar`.

### X3 — Component need: most data lists should be real data tables, not stacked card rows

Directly requested: audit every collection currently rendered with
`style.css`'s `.rows`/`<li>` stacked-card pattern (`.rows li` — flex row,
avatar, name/sub-line, hover background, used everywhere from
`admin/users.html`'s practitioner list to `client-detail.html`'s session
list to the public directory) and separate genuinely tabular data (fixed
columns, meant to be scanned/sorted/compared row-by-row) from genuinely
card-like data (variable-length content, or an interaction — like inline
expansion or an embedded form — that a `<tr>` can't cleanly host).

**Convert to a real data table:**

1. **`static/admin/users.html`** — the Practitioners tab (`practitionerRow()`)
   and Admins tab (`adminRow()`). Columns: Name/email, Status, Plan,
   Clients, Views, Contacts, Actions. Today each row is its own wrapped
   flex block with a second async-loaded "stats" line underneath
   (`data-stats-for`) — none of the seven data points line up between
   rows, so comparing two practitioners' client counts means reading two
   different vertical positions. A table's fixed columns fix that for
   free, and unlock client-side sort (by status, plan, or client count)
   over the array `renderPractitioners()` already holds in memory — no new
   endpoint, same "fine at 10-20 scale" reasoning
   [16](16-users-page-redesign.md) already used for search.
2. **`static/practitioner/clients.html`** — the client roster (`row()`).
   Columns today would just be Name/Email; worth adding Last session date
   and an intake-submitted indicator as columns once this converts, since
   [05 · Practitioner portal](05-practitioner-portal.md#pro-plan) describes
   a Pro practitioner's client list as something that grows over the life
   of a practice, not a fixed small set.
3. **`static/admin/questionnaires.html`** — the "Previous versions" list
   (`questionnaireRow()`). Columns: Title, Version, Actions. Lower
   priority (typically a handful of rows at a time) but the same shape
   problem as #1, and directly named in [ADM1](#adm1--medium-two-lists-that-will-outgrow-a-handful-of-rows-have-no-sort)
   above.
4. **`static/admin/dashboard.html`** — the "Pending applications" panel
   (`pendingRow()`). Columns: Name, Email, Action. Converting this
   alongside #1 also closes a small drift risk: this is the same
   `pending`-status practitioner data `admin/users.html` renders, styled
   differently in two places today.

**Leave as-is, and why:**

- **`static/public/directory.html`**'s `.coach-grid` — a browse/discovery
  surface modeled explicitly on vibly.io's card pattern
  ([03](03-website.md#practitioner-directory)), photo-first with
  variable-length bio text. This is the one case in the brief's own example
  list that's clearly not tabular — forcing it into rows/columns would
  undermine the "browse and pick a person" framing the page exists for.
- **`static/index.html`**'s `#source-list` (`.src` cards, admin's
  knowledge library) and **`static/practitioner/knowledge.html`**'s source
  rows — each card carries a variable-length summary, topic tags, and (on
  the practitioner side) an inline slider-plus-Save mini-form. A table cell
  can't hold a paragraph-length summary without breaking row alignment, and
  an embedded form control per row is exactly the case data tables handle
  worst.
- **`static/practitioner/contacts.html`** — each row has a message body of
  arbitrary length; this reads as an inbox, not a table. If message volume
  ever grows enough to need sorting, the right move is a compact table for
  Name/Status/Date with the message revealed on row-click — not forcing
  the message itself into a cell.
- **`static/practitioner/client-detail.html`**'s session list
  (`sessionRow()`) and "Reports & documents" panel (`documentRow()`) —
  each session row expands in place into a full sub-editor (past turns
  plus two document textareas with their own Save/Mark-final buttons,
  `expandSession()`). A `<tr>` can't cleanly host a multi-field form
  opening beneath it without breaking table semantics — this needs to stay
  an expandable list.
- **Admin's audit trail** (`#audit`, `.log` in `static/index.html`) — an
  append-only activity feed, conventionally read top-to-bottom as a
  timeline (each entry already reads like a log line: actor, action,
  detail, timestamp), not something a user sorts or compares row-by-row.
- **`static/client/files.html`**'s uploaded-files list — a handful of
  files per client at this product's stated scale. Revisit if/when a
  client's file count grows past a screenful; not worth the conversion
  today.

**Concrete component approach.** Material Web has no data-table component
— confirmed against [15 · Design system](15-design-system.md)'s full
component-migration list (buttons, text fields, select/menu, dialog,
snackbar, chips, list rows — no table). Two options:

- **(a) A plain semantic `<table>` styled against the existing MD3 tokens
  — recommended.** `style.css` already has a `.tbl` class, but it's built
  for exactly two static, read-only, two-column stat tables
  (`admin/dashboard.html`'s Site overview/Knowledge library panels) — no
  header row, no sort, no row actions, `td:not(:first-child)` hardcoded to
  right-align (fine for a number column, wrong for an Actions column).
  Evolve this into a new `.data-table` pattern: a real `<thead>` with
  clickable `<th>` for sortable columns (client-side `Array.prototype.sort`
  over the array each page already holds — no new endpoint anywhere in
  this list), a small ascending/descending chevron reusing the app's
  existing inline-SVG icon style, `.chip` used inside cells exactly as it
  already is in card rows (no new visual language for status/plan), row
  actions right-aligned in a fixed last column instead of today's
  `flex-wrap`, and row hover reusing `.rows li:hover`'s `--panel-2`
  background so a table row and a card row still feel like the same
  product.
- **(b) A JS grid library** (TanStack Table, AG Grid, etc.) — considered,
  rejected. Disproportionate for lists sized at "10-20 practitioners," a
  single-digit admin roster, and one practitioner's own client list — the
  same "at this project's size" reasoning
  [15](15-design-system.md#why-full-material-web-not-tokens-only) used to
  justify adopting Material Web itself doesn't clear the bar for a second,
  heavier dependency layered on top of it.

### X4 — Medium: onboarding is individually-good empty states with no cross-page checklist

Every empty state in the app names its next action (`empty()` in
`shared.js`, used consistently — confirmed as a strength, not a gap, by
[14](14-ux-findings-v2.7.md#cross-portal-consistency-notes)). But a brand-
new Pro practitioner's actual first-run path spans three separate pages
with no visible thread connecting them: `profile.html` to set an Anthropic
key (already the subject of a proactive banner on Consult per
[14 §P7](14-ux-findings-v2.7.md#p7--medium-profile-pages-anthropic-api-key-panel-is-easy-to-miss-on-first-pro-upgrade),
resolved), `clients.html` to add a first client, `consult.html` to ask a
first question. Nothing surfaces "you're 1 of 3 steps in" anywhere, despite
`dashboard.html`'s `#welcome-panel` already being the natural home for
exactly that kind of summary (it currently just shows name/plan/status
chips).

**Fix direction:** a small first-run checklist card on the practitioner
dashboard — "Set your API key · Add a client · Start a consultation" —
each item a link to the relevant page, each auto-checked off from data the
dashboard already fetches (`p.has_anthropic_key`, `clients.length > 0`,
`sessions.length > 0`), reusing the numbered `.step` circle marker already
established on `static/index.html`'s "Teach Clinic / The library / What
Clinic knows" three-step admin panel — same visual idiom, new context.
Hides itself once all three are done, same as `#nav-upgrade` already hides
itself once a practitioner is on Pro.

### X5 — Low: the motion system is well-built but only fires on entrance

`style.css`'s motion layer (`liftIn`, `slideL`, `popIn`, the wordmark's
`sway`, the empty-state `leafmark`'s `breathe`) is a genuine strength —
purposeful, short, respects `prefers-reduced-motion`. But it's applied only
to things appearing on the page, not to values changing on it: dashboard
stat cards (`statCard()` on both `practitioner/dashboard.html` and
`client/dashboard.html`) and `admin/dashboard.html`'s `.tbl` numbers render
their final value instantly. Every other part of the product feels
considered in motion; the numbers a user actually opens the dashboard to
check are the flattest thing on the page.

**Fix direction:** a small count-up animation (0 → final value over
~350-400ms, the `--ease` cubic-bezier already defined at the top of
`style.css`) on stat card numbers when they first render — CSS/JS only, no
new dependency, same restraint the rest of the motion system already
practices.

---

## Redesign direction

### Golden path 1 — practitioner reviewing intake before consult

This path is close to done. [P1-P9](14-ux-findings-v2.7.md#practitioner-portal)
already fixed the structural breaks (Start consultation deep-links to the
right client, Resume actually resumes, intake sits in Consult's own
overview panel, the two document audiences are visually separated). What's
proposed here is finish, not repair:

```
Dashboard (welcome panel + first-run checklist, X4)
  → Consult (client picker, client overview panel shows intake + recent sessions)
      → "Details" link → client-detail.html (Intake review tab, default)
          → clinician notes per theme
          → "Start consultation" → back to Consult, deep-linked to this client
      → Ask Clinic → live agent-progress toast (already shipped, 15 §Live agent toast)
          → verified answer + sources → optional Clinician note / Client report
```

The only two changes proposed against this loop: [PRAC1](#prac1--medium-add-a-client-is-still-a-native-details-disclosure-unlike-admins-equivalent-form)
(dialog-based add-client, so a growing roster doesn't repeat admin's old
U4 problem) and [PRAC2](#prac2--low-three-different-hand-rolled-tab-idioms-now-exist-none-of-them-md-tabs)
(`md-tabs` on client-detail.html). Everything else in this path is layout
polish already covered above, not a flow break.

### Golden path 2 — client discovering a practitioner → signing up → intake

Booking/scheduling and telehealth are explicitly out of scope
([01](01-overview.md#out-of-scope--deliberately)), so this path's endpoint
is intake completion, not a live consultation — the client-side "golden
path" is discovery → account → questionnaire, full stop:

```
Directory (browse/filter, PUB3: add search)
  → Coach detail (PUB2: clarify contact-form vs. become-client hierarchy)
      → Sign up (practitioner preselected via ?practitioner_id=)
          → Log in
              → Questionnaire (CLI1: fix shell; client's true first landing page)
                  → confirmation state already links to Files + Wearables
```

The one structural gap in this path is [CLI1](#cli1--high-the-clients-documented-first-landing-page-uses-the-old-page-shell)
— every other step in this list already works end-to-end (H1/H2 from
[13](13-known-issues.md) closed the two ways this used to break). The rest
of what's proposed for this path is the visual-identity gap at the top of
the funnel ([PUB2](#pub2--medium-coachhtml-stacks-two-same-weight-ctas-with-no-framing-for-which-to-use),
[PUB5](#pub5--low-the-directory-and-about-page-have-no-visual-identity-beyond-the-card-grid)),
not a missing route.

### Visual/interaction ideas {#visual-interaction-ideas}

Grounded in what's actually missing today, not a generic "add more
gradient" pass — the glass/gradient/botanical language in
[15](15-design-system.md) is already distinctive; these extend it into
places it hasn't reached yet, using components and motifs the app already
has:

- **Directory hero line.** One sentence of `.hint`-styled copy above the
  filter row on `directory.html` — "Independent practitioners, vetted and
  approved by Clinic — browse by specialty or search by name." — plus a
  `.vine` divider before the grid starts, matching the divider already
  used on `coach.html`/`about.html`. No new component.
- **First-run checklist** (X4) reusing the `.step` numbered-circle marker
  already established on the admin knowledge dashboard's three-panel
  layout — same visual grammar, applied to a second "walk me through this"
  moment instead of inventing a new one.
- **Stat count-up** (X5) on every dashboard's numeric stat cards — cheap,
  reuses the existing `--ease` token, no new dependency.
- **Botanical motif on the become-client CTA.** `coach.html`'s
  `#signup-panel` is a bare flex row today; Consult's `#ask-panel` already
  demonstrates the `.leafmark` watermark pattern (a faint background leaf
  behind a panel that matters). Once [PUB2](#pub2--medium-coachhtml-stacks-two-same-weight-ctas-with-no-framing-for-which-to-use)
  promotes this panel to the primary CTA, giving it the same watermark
  treatment visually reinforces "this is the one that matters" without new
  copy or a new component.
- **Empty-state parity for the new data tables** (X3) — extend the
  existing `empty()` helper's leaf-watermark treatment to a table's
  zero-results state (e.g., a search that matches nothing), so the new
  component doesn't look like a different, blanker product next to every
  other empty state in the app.

### Component needs, summarized

- **`md-tabs`/`md-primary-tab`** — replaces two hand-rolled idioms
  ([X2](#x2--medium-three-tab-idioms-one-md3-component-that-should-replace-all-of-them)).
- **A new `.data-table` pattern** (plain `<table>`, MD3-token-styled,
  evolved from the existing `.tbl` class) — no MD3-native option exists;
  see [X3](#x3--component-need-most-data-lists-should-be-real-data-tables-not-stacked-card-rows)
  for exact scope (convert/leave-alone lists) and the rejected grid-library
  alternative.
- **`md-dialog`** — already adopted by `admin/users.html`
  ([16](16-users-page-redesign.md)); extend the same pattern to
  `practitioner/clients.html`'s add-client form
  ([PRAC1](#prac1--medium-add-a-client-is-still-a-native-details-disclosure-unlike-admins-equivalent-form)).
- **No new components needed** for chips, selects, snackbars, or buttons —
  those are already MD3 and already consistent; nothing found in this
  walkthrough warrants touching them.

## What's explicitly out of scope

- **Booking/scheduling, telehealth video, client-to-practitioner
  payments** — unchanged from [01](01-overview.md#out-of-scope--deliberately);
  golden path 2 above is scoped to intake completion, not a live
  consultation, for exactly this reason.
- **A JS data-grid dependency** — considered for [X3](#x3--component-need-most-data-lists-should-be-real-data-tables-not-stacked-card-rows),
  rejected as disproportionate for this product's stated scale.
- **`/admin/users`'s own layout** — already redesigned
  ([16](16-users-page-redesign.md)); this document only proposes the
  additive data-table treatment on top of that redesign's existing tabs/
  search/dialog structure, not a re-litigation of it.
- **File delete on `client/files.html`** — flagged in
  [CLI2](#cli2--low-uploaded-files-show-name-and-date-only) as **requiring
  new backend work** (`DELETE /api/me/files/{id}` doesn't exist today);
  not designed further here.
- **A plan filter on `admin/users.html`** — named as a small prerequisite
  for [ADM2](#adm2--low-dashboards-stat-numbers-dont-link-to-the-filtered-list-that-explains-them)'s
  "Pro plan" deep link, not designed in full here (same shape as the
  existing status filter, left as a follow-up detail).
- **Email/notifications** — unchanged, still deferred per
  [13 · M1](13-known-issues.md#m1--no-emailnotification-system-exists-anywhere-in-the-codebase--deferred).
