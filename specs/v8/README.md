# v8 — Full UX/UI redesign

**Status: spec only — not implemented.** One single document, per
explicit instruction. Nothing here is built; this is the research,
architecture, and design-direction document to be reviewed before any
implementation phase starts.

## 0. Brief, as given

"Redesign, including layout and everything. Preserve only the color
and logo/branding. Act as a senior UX researcher and UI designer to
figure out the best experience and user flow for the users." Plus,
folded in as the brief evolved: rebuild the Graph view to be genuinely
light; rebuild the landing page with animation and an animated
background, add the "necessary" pages a real product needs, and
highlight *available* practitioners on it; some admins also hold a
practitioner profile (not all — an optional link, not a merged role),
so the account model needs to support that; the practitioner Profile
page needs real profile-building forms; this is an EU-targeted
application, so legal/compliance pages and disclaimers are required.

**What's locked**: the color tokens in `app.css`'s `:root` (`--bg`,
`--panel`, `--ink`, `--accent` and its family, the `--rail-*` gradient
trio) and the `Sprig` mark / "Clinic" wordmark. **Everything else is
open**: layout, navigation paradigm, type, spacing, motion, component
visual language, information architecture, page inventory.

## 1. Method

This is not a generic redesign written from a blank page — the app
has a real history (`specs/v1` through `v6.20`, this repo's own
changelog) including two live "act as a real user" audits
(`specs/v6.6`, and the `v6.16` combined PM+QA subagent audit), several
rounds of live bug reports from actual use, and this session's own
direct observation of every portal's current code. The research
synthesis below is built from that real evidence, not assumed.

## 2. Research synthesis

### 2.1 What's actually wrong, by evidence

| Finding | Source | Implication for IA/layout |
|---|---|---|
| Admin Library page has 3 view modes, a folder tree, a Tree-view tab, a (removed, to be rebuilt) Graph-view tab, sort, bulk actions, a per-document "⋮" menu with 6 items, and 4+ dialogs, all on one page | Direct observation, `v6.11`-`v6.20` history | This is the single most-used admin surface and it grew feature-by-feature with no holistic IA pass. It needs to *be* the admin home, not a tab competing with Dashboard. |
| `.rail-layout` utility in `app.css` already exists specifically because "several portal screens... stack a secondary panel... which reads as cramped" | `app.css`'s own comment, written before this spec | The app has been organically reaching for a "rail + contextual panel + main content" pattern (Library's folder sidebar, Consult's chat sidebar) without ever formalizing it as a real layout primitive. Formalizing it, not inventing something new, is the right fix. |
| Icon-only rail requires a hover tooltip or an onboarding tour to be legible at all | `v7/06`'s own tour build was partly compensating for this | An icon-only nav for 5-8 items per portal is an information-scent problem a label-visible rail solves at the source, instead of compensating for with a tour. |
| Table view silently lacked parity with Icons/List (found by the `v6.16` audit, fixed in `v6.17`); search doesn't work outside the Library tab; bulk actions cover only private/public | `v6.16`/`v6.17` | Feature parity gaps are a symptom of building each view/tab as its own bespoke surface instead of one shared page template. A real template system prevents this class of bug by construction. |
| Dashboards (all three portals) are passive stat tiles, not actionable — no "here's what needs you right now" | Direct read of all three Dashboard pages | A dashboard that just restates counts the admin/practitioner already half-knows is lower value than one that surfaces the 2-3 things actually needing a decision today. |
| Ingest terminology sprawl: "staged" → "queued" → "Ingesting…" → a bell icon → "Placed in library" — five words for one linear process | `v6.16` audit finding (deferred, not fixed) | A real redesign is the right place to collapse this to one consistent mental model, not a one-line copy patch. |
| Wearables page once implied live vendor data when it was fixture data; a questionnaire ignored its own typed schema; a suspended client could still log in | `v6.6` live audit | The client portal in particular has a track record of showing things that aren't true yet. Any redesigned client surface must default to honest, explicit "not available yet" states, not optimistic ones. |
| No practitioner "accepting new clients" signal exists anywhere in the data model | Checked live, this session | The landing page can't honestly highlight "available" practitioners today — this is a new field, not a surfacing problem. |
| Admin and practitioner accounts are two fully separate tables/roles with no link between them | `app/core_store.py`'s schema, checked this session | Supporting "this one person is both an admin and a practitioner" needs a real schema decision (§4), not a UI-only fix. |
| No legal/compliance pages exist at all (no privacy policy, terms, cookie notice, medical disclaimer) | Checked live, this session | For an EU-facing health-adjacent product this is a real gap, not a nice-to-have (§8.5). |

### 2.2 Personas and jobs-to-be-done

**Admin** — a clinic operator/curator. Job: *get new source material
graded, organized, and trustworthy-searchable with minimum friction;
know immediately if something's broken (a failed ingest, exhausted
billing, a crashed service).* Secondary job: manage who has access
(practitioners, other admins, client accounts). Pain today: the
primary job (Library) and the secondary job (Users/Questionnaires/
Audit) compete for equal-weight nav real estate even though their
usage frequency isn't remotely equal.

**Practitioner** — a clinician. Job: *pull up a specific client's
context fast and get a trustworthy, cited answer to inform care,
during or between real consultations.* Secondary jobs: manage the
client roster, keep a profile that attracts new clients (if accepting
them), tune which library content their own answers draw from. Pain
today: Consult (the core loop, already well-designed per this
session's own read) is one of eight equal-weight rail items, not the
default landing experience for a Pro practitioner.

**Client** — a patient, did not choose this software, has the least
investment in learning it. Job: *do the thing my practitioner asked
(a questionnaire), see what's in my record, trust that it's private.*
Pain today: five disconnected pages with no single "here's what's
next" thread tying them together.

**Prospective practitioner / prospective client (public site
visitor)** — job: *decide, fast, whether this is credible enough to
apply to join or to trust with health information.* Pain today: the
landing page is a well-written but entirely static pitch — no social
proof, no visible practitioners, no sense of an active, real platform.

## 3. Brand constraints (locked)

- Color tokens: `--bg`, `--panel`, `--panel-2`, `--line`, `--line-2`,
  `--ink`, `--ink-2`, `--muted`, `--accent`/`--accent-ink`/
  `--accent-soft`, `--ok`/`--warn`/`--danger` families, and the
  `--rail-top`/`--rail-bottom`/`--rail-indicator` gradient trio —
  unchanged values. `app.css` itself already documents this gradient
  as "kept literal per spec, rejected any reinterpretation" — a
  decision already made twice in this project's history; this spec
  makes it three times, now extended to the whole redesign.
- The `Sprig` botanical mark and the "Clinic" wordmark — unchanged.
- Everything else named in §0 is open, including whether the rail
  itself survives as a concept (§5 argues it should, evolved, not
  discarded — a reasoned decision, not an assumption).

## 4. Account model: admin ↔ practitioner linking

Direct requirement, clarified: **not all admins are practitioners** —
some admins additionally hold a practitioner profile; this is an
optional link between two still-distinct account types, not a merged
role.

### 4.1 Schema

- `admins` gains `linked_practitioner_id TEXT REFERENCES
  practitioners(id)` (nullable) — `ALTER TABLE admins ADD COLUMN IF
  NOT EXISTS linked_practitioner_id TEXT REFERENCES
  practitioners(id);`, same idiom every other schema addition in this
  codebase already uses.
- A superadmin-only action sets/clears this link (reuses the existing
  `require_superadmin` dependency — linking accounts is an identity/
  trust decision, not a plain-admin one). Exposed from the admin
  Users page (§7.2).
- **Not** the reverse (no `practitioners.linked_admin_id`) — the
  relationship only needs to be looked up starting from the admin
  side (session → "do I also have a practitioner view available?"),
  and a single FK avoids a two-way-sync integrity problem for no
  benefit.

### 4.2 Session & switching UX

- Login stays exactly as it is today — one email, one password, one
  `role` claim (`admin`). No second login, no role picker at
  sign-in.
- `GET /api/auth/me` (already enriched once this session, for
  `tour_completed` — §4 of `v7/06`) gains one more live-looked-up
  field: `has_practitioner_view: bool` (true when
  `linked_practitioner_id` is set).
- The new Top Bar (§5.2) shows a portal switcher **only** when
  `has_practitioner_view` is true — "Admin view / Practitioner view,"
  a plain client-side navigation between `/admin/*` and
  `/practitioner/*`, no new session or re-auth. Each portal's own
  existing auth guard (`require_admin`/`require_practitioner`) keeps
  working unmodified — the switcher is a convenience link, not a new
  trust boundary; both of this person's accounts already independently
  satisfy their own portal's real auth check.
- An admin without a linked practitioner profile sees no switcher at
  all — zero UI change for the common case.

### 4.3 What this does not change

No merged permissions, no single account holding both role claims at
once, no change to either existing auth dependency's own logic. A
linked person is still, structurally, two separate accounts (two
separate `id`s, two separate password hashes, two separate sessions
when logged into each) that happen to know about each other for
navigation convenience.

## 5. New layout system

### 5.1 Keep the rail concept, evolve its information design

Argued, not assumed: the icon rail's gradient *is* explicitly locked
brand identity (§3), and discarding the rail-as-a-shape (not just its
color) in favor of, say, a top-only nav would be solving a problem
(icon-only legibility) with a bigger change than it needs. The actual
problem is information density, not the rail's existence:

- **Wider, label-visible by default** — not icon-only with a hover
  tooltip. A persistent icon + label pair, same gradient, same
  position; collapses to icon-only only on a genuinely narrow
  viewport (replacing today's "bottom bar under 720px" breakpoint
  behavior, kept as-is since it already works).
- **Grouped**, not a flat list — each portal's items split into a
  primary group (the portal's actual job-to-be-done pages — Library
  for admin, Consult for practitioner) and a secondary group (account/
  settings-shaped pages — Users/Questionnaires/Audit for admin,
  Profile/Upgrade for practitioner), visually separated by a thin
  divider, not just ordered.
- **The portal switcher** (§4.2), when present, sits in the rail's own
  footer area, next to the existing sign-out control — a role-level
  action, grouped with the other role-level action already there.

### 5.2 A new global Top Bar (genuinely new — today there is none)

Every portal currently has zero top bar; content starts immediately
next to the rail. A persistent top bar is added, consistent across
all three portals (and a lighter variant on the public site):

- **Left**: a breadcrumb reflecting the current page's place in that
  portal's IA (e.g., "Library / Hormones / Menopause" — reuses the
  exact breadcrumb logic the admin Library page already built for its
  own folder navigation, promoted to a shared `Breadcrumb.svelte`
  component instead of staying page-local).
- **Center-right**: the search/command-palette trigger, **promoted**
  from today's easy-to-miss rail icon to a persistent, always-visible
  search field in the top bar itself (still opens the existing
  `CommandPalette.svelte` on click or `Cmd/Ctrl+K` — same component,
  better discoverability, which was this exact feature's own stated
  weakness when it shipped).
- **Right**: the portal switcher (§4.2, when applicable) and the
  existing user/sign-out area, moved up from the rail footer into the
  top bar's corner — a more conventional, more discoverable location
  for "who am I, how do I leave" than a rail footer icon.

### 5.3 The three-zone content area, formalized

Every page in every portal is now explicitly one of:

1. **Rail + Top bar + Main content** (no contextual panel) — simple
   pages: Dashboard, Profile, Questionnaires, Audit history, Contacts.
2. **Rail + Top bar + Contextual panel + Main content** — pages with
   a real secondary navigation/filtering concern of their own:
   Library (folder tree), Consult (client list + history, already
   built this way), Users (role/status filters), Clients (status/
   search filters). The contextual panel is now one real, shared
   layout primitive (building directly on the existing `.rail-layout`
   CSS utility `app.css` already has, rather than each page's own
   bespoke sidebar CSS) — not a new invention, the formalization of a
   pattern the codebase already reached for three separate times.

### 5.4 Responsive rule

Same floor as today (`v7`'s own responsive work): no page scrolls
horizontally, a 400px viewport stays usable, the contextual panel
(§5.3's second shape) collapses above the main content on narrow
viewports rather than beside it — the exact behavior the admin
Library page's folder sidebar already has at 900px, promoted to the
shared primitive's own default rather than reimplemented per page.

## 6. Page template system

Five templates, each a real shared component (not a convention
enforced by code review alone — a template an engineer imports, the
same discipline `Card`/`EmptyState`/`Skeleton` already established in
`v7/01`):

- **List/Browse** — search, filter row, optional view-mode toggle,
  optional sort control, a content area, pagination. Replaces the
  bespoke top-of-page markup every list-shaped page (Library, Users,
  Clients, Audit, Questionnaires) currently hand-rolls slightly
  differently. The view-mode toggle and sort control are opt-in slots,
  not forced on every page (Audit history has no reason to offer an
  Icons/Table toggle, say).
- **Detail/Record** — a document/client/practitioner's own page:
  header (title + primary actions), a tabbed or sectioned body. The
  already-promoted-this-session `(admin)/admin/[id]` and
  `(practitioner)/practitioner/knowledge/[id]` detail pages are the
  model to formalize, not replace.
- **Dashboard/Overview** — **redesigned**, not just restyled: a
  "needs your attention" section (first, above the fold — pending
  applications, failed ingests, new contacts, whatever that portal's
  own actionable items are) ahead of the passive stat-tile grid, which
  moves to a secondary "at a glance" position below it. Directly
  answers the "passive stats" finding in §2.1.
- **Form/Wizard** — a single-column form shell with inline validation
  (not submit-time-only) and a clear primary action, used for every
  create/edit flow (Add client, the practitioner Profile builder in
  §9, the public `/join`/`/signup` flows).
- **Chat/Conversational** — Consult's existing shape, formalized as
  its own template since the client portal's own redesign (§10.3) may
  reasonably want a lighter conversational pattern for "ask your
  practitioner a question" in the future, even though that's out of
  this spec's immediate scope.

## 7. Admin portal redesign

### 7.1 Information architecture

Library **becomes the admin portal's default landing page** (not
Dashboard) — it's the actual job-to-be-done, per §2.2. Dashboard
survives as a real, secondary nav item, redesigned per §6's
Dashboard/Overview template (platform-wide pending applications, new
contacts, and — new — failed/stuck ingestion jobs surfaced directly,
not just the aggregate queue-status line the Library page already has
buried in it).

Rail groups:
- **Primary**: Library (icon: book)
- **Secondary**: Dashboard, Users, Questionnaires, Audit history

### 7.2 Users page gains the admin↔practitioner link control

Per §4.1 — a superadmin viewing a practitioner's row in the Users page
gets a new action ("Link to an admin account" / "Unlink"), alongside
the existing approve/suspend/plan-change actions already there.

### 7.3 Library, using the new templates

- List/Browse template: the existing search/filter/view-toggle/sort
  row (`v6.20`'s own sort work) slots in directly — no redesign needed
  there, just a template-ification of what already works.
  Contextual panel: the folder tree (unchanged logic, restyled to the
  new token set).
- Terminology collapse (§2.1's "five words" finding): **staged items
  render as cards with the literal word "Processing"** through every
  step (reading/chunking/embedding/extracting/writing collapse to one
  progress bar under that one word, detail text still available on
  hover/expand for anyone who wants it) — "queued" stays as a distinct,
  honest state (genuinely different from "processing," worth its own
  word) but "Ingesting…"/the bell icon's implicit "needs finalization"
  state/"Placed in library" collapse into: **Processing → Needs review
  (the bell, renamed to a plain label, not just an icon) → Done**.
  Three states, three words, not five.

### 7.4 Graph view — rebuilt, canvas-based, genuinely light

Direct requirement: rebuild it, make it light. Root-caused this
session (`v6.18`) that the SVG-based version's real cost was DOM
node count × stroke-outlined text paint, not the physics simulation
itself. A canvas rebuild removes that cost structurally rather than
mitigating it:

- **`<canvas>`, not SVG** — every node/edge becomes a 2D canvas draw
  call instead of a DOM element; a redraw touches zero DOM nodes
  regardless of graph size. This is the standard scalability fix for
  force-directed graphs at this node count, not a novel idea — the
  original `v6.13` spec considered and rejected a canvas-based
  wrapper library (`force-graph`) specifically for its *dependency
  weight*, not its rendering approach; this rebuild keeps that
  reasoning (still no wrapper library, still `d3-force` directly for
  physics) while adopting canvas for the *draw* step only, where the
  real performance problem actually lived.
- **Labels off by default, not conditionally rendered** — `v6.18`'s
  fix made labels conditional on zoom/hover past a node-count
  threshold; the rebuild goes further: no label text is drawn at all
  until the admin hovers a specific node (a single canvas `fillText`
  call for one label, not a pass over the whole node set) or the
  graph is small enough (≤20 nodes) that showing all of them costs
  nothing. This removes the single largest cost `v6.18` could only
  reduce, not eliminate.
- **A capped, resolution-independent node budget** — `concept_graph()`'s
  `limit` stays server-side-bounded (currently 80; revisit the exact
  number against real canvas-frame-time measurement once built, not
  picked blind here) — rendering cost no longer scales with DOM at
  all, so this cap exists for Neo4j query cost and visual
  legibility, not render performance.
- **Re-added to the Library IA** as a third List/Browse view-mode
  option alongside Icons/List/Table (not a separate tab the way
  `v6.13` first shipped it) — consistent with §6's template system:
  a graph is just another way to browse the same document set, not a
  structurally different page.

## 8. Public site redesign

### 8.1 Landing page — rebuilt, animated

- **Animated background**: the existing `body::before`/`body::after`
  radial-gradient drift + botanical-line-texture layers in `app.css`
  already exist and already animate (`@keyframes drift`, 34s,
  `prefers-reduced-motion`-safe) — site-wide, not landing-page-
  specific. The landing page's own rebuild adds a **second, dedicated
  hero-level animated layer**: a slow-moving particle/connection-line
  field (canvas, same rendering choice as §7.4 for the same reason —
  cheap, DOM-free, scales to any viewport) suggesting the knowledge-
  graph concept visually, using only the locked accent colors —
  this is new content, not a reskin of the existing ambient background.
- **Content animation**: `v7/02`'s scroll-triggered reveal
  (`reveal.ts`, already built) extends to every new section below.
- **Highlight available practitioners** (direct requirement, repeated
  twice): a new "Meet the practitioners" section, pulling the first
  N practitioners where `accepting_new_clients = true` (§9's new
  field) from the public directory's own existing data, each as a
  compact card (photo, name, 1-2 specialties, a "View profile" link
  into the existing `/coach/[slug]`-style detail page). Genuinely new
  section, not a restyle of anything that exists today.

### 8.2 Necessary additional pages

Beyond what exists (`/`, `/about` [redirects to `/`], `/practitioners`,
`/join`, `/login`, `/signup`, `/account`, `/coach`):

- **`/pricing`** — if the product has a real pricing model to show
  (the `practitioners.plan`/`stripe_*` columns imply one exists
  server-side already) — a real content decision for the user, not
  assumed here; flagged as a gap, not filled with invented numbers.
- **`/faq`** — common visitor questions (how grounding/citation works,
  how a practitioner gets approved, what happens to client data) —
  content drafted collaboratively once this spec is approved, not
  invented wholesale here.
- **`/contact`** — a real, direct contact path independent of the
  practitioner-specific contact-form flow that already exists.

### 8.3 Practitioner Profile — a real profile-builder form

Direct requirement: "add necessary forms and whatnots to build the
profile page." The `practitioners` table already has the right
columns for a rich profile (`photo_path`, `bio`, `specialties_json`,
`languages_json`, `years_experience`, `consultation_price_cents`) —
confirmed by reading the schema this session — but today's
`/practitioner/profile` page (56 lines, read this session) doesn't
expose a form for most of them. The Form/Wizard template (§6) applies:

- Photo upload (reuses whatever upload mechanism the admin Library's
  own file-upload flow already has, not a new one).
- Bio (a plain textarea, with a sane character guidance, not a hard
  limit presented as an error).
- Specialties — a multi-select/tag-input over a fixed, admin-
  maintained taxonomy (consistency for the public directory's own
  filter UI, not free text sprawl).
- Languages — same multi-select pattern.
- Years of experience, consultation price — plain numeric fields.
- **New**: "Accepting new clients" — a toggle, the field §8.1's
  landing-page highlight and the public directory both read from.
  Doesn't exist in the schema today (checked live, this session) —
  `ALTER TABLE practitioners ADD COLUMN IF NOT EXISTS
  accepting_new_clients BOOLEAN NOT NULL DEFAULT FALSE` (defaults to
  *off* — a practitioner opts in explicitly, never auto-listed as
  available before they've said so).

### 8.4 Public directory (`/practitioners`) and `/coach/[slug]`

Not read in detail this pass (flagged, same as `v7/02`'s own stated
gap) — gets its own focused read-then-design pass when scheduled,
applying the List/Browse template and surfacing the new
`accepting_new_clients` field as a real filter, not just landing-page
decoration.

### 8.5 EU legal & compliance pages (new — direct requirement)

None of the following exist today (checked live); all are real gaps
for an EU-facing product, not optional polish:

- **`/privacy`** — a privacy policy: what's collected, why, lawful
  basis, retention, third-party processors (Nebius, Anthropic, Stripe
  — every one of this app's own real sub-processors, named
  accurately, not boilerplate).
- **`/terms`** — terms of service for both practitioner and client
  account types (they have genuinely different obligations — a
  practitioner is a data controller for their own clients' records in
  a meaningful sense; a client is a data subject).
- **A cookie/consent notice** — this app's own cookies today
  (confirmed: a signed session cookie, `httponly`, no third-party
  tracking cookies found in `app.css`/the routes read this session)
  are plausibly "strictly necessary" under the ePrivacy directive,
  which wouldn't legally require a consent banner — a real
  determination needing actual legal review, not assumed here either
  way. The spec's obligation is to flag this decision point, not
  guess at it.
- **A medical/clinical disclaimer** — surfaced at the point it matters
  most: the Consult page's answer area and the client-facing
  questionnaire/record pages — "this is a decision-support tool for a
  licensed practitioner, not a replacement for professional medical
  judgment, and not a source of direct medical advice to a client" (or
  the user's own accurate wording) — a persistent, unobtrusive footer
  note, not an interstitial a user has to click through.

**None of this spec's legal page *copy* is binding legal text** — this
section specs the pages' existence, placement, and structural content
(what sections each page needs), not the actual compliant wording,
which needs real legal review before publishing regardless of how
this spec's draft reads.

## 9. Practitioner portal redesign

### 9.1 Information architecture

Consult **becomes the practitioner portal's default landing page**
for a Pro practitioner (per §2.2's JTBD finding) — Basic-plan
practitioners (locked out of Consult today via `require_pro_
practitioner`) land on Dashboard instead, same as today's behavior,
just no longer the universal default for every plan tier.

Rail groups:
- **Primary**: Consult, Clients
- **Secondary**: Contacts, Library weights (Knowledge), Questionnaires,
  Profile, Upgrade

### 9.2 Everything else

Consult itself is not redesigned beyond token/template adoption (§6,
§2.1 — already well-built, confirmed this session). Clients/Contacts
adopt the List/Browse template. Profile gets §8.3's real form.

## 10. Client portal redesign

### 10.1 Information architecture

Per §2.2, the least sophisticated audience gets the most consolidated
IA: Dashboard is redesigned (§6) from a passive 4-tile grid into a
single **"Your care" stream** — one scrollable timeline-shaped page:
an unanswered questionnaire (if any) at the top as a clear next
action, recent health-record entries, recently shared files — the
other portal's separate nav items (Questionnaire/Health record/Files)
remain reachable from the rail for direct navigation, but Dashboard
itself stops being a 4-tile menu and becomes the actual "what's
next" answer §2.1 found every dashboard in this app currently lacks.

### 10.2 Wearables — stays exactly as `v6.6` already fixed it

An honest "Coming soon" state — no change; this redesign's own stated
principle (§2.1, "default to honest, explicit not-available-yet
states") is already satisfied here, confirmed by that prior live
audit's fix, not something to touch again.

### 10.3 What this does not change

No new conversational/chat-shaped surface for the client portal in
this pass (flagged in §6 as a reasonable future direction, not built
here) — out of this spec's immediate scope.

## 11. Design system (supersedes `v7/01`)

`v7/01`'s additive tokens (named weights, durations, easing curves,
`--container-max`) carry forward unchanged — nothing here removes
them. New, specific to this redesign:

- **Top bar height/elevation tokens** — a new `--topbar-h` (consistent
  across all three portals + the lighter public variant) and a
  dedicated shadow weight distinguishing it from `--shadow`/
  `--shadow-lg`'s existing two steps.
- **Rail width token** — `--rail-w-expanded` (the new label-visible
  default) and `--rail-w-collapsed` (icon-only, narrow-viewport
  fallback), replacing today's single hardcoded `4.75rem` literal in
  `AppRail.svelte`.
- **Contextual-panel width token** — `--panel-w` (currently a bespoke
  `22rem` in `.rail-layout` and a bespoke `18rem` in Consult's own
  `.sidebar` — one shared value once both adopt §5.3's formalized
  primitive, unless a real content reason justifies keeping them
  different, decided when each page is actually migrated, not
  pre-decided here).

## 12. Accessibility & responsive

Same floor `v7` already established (focus-visible outlines,
`prefers-reduced-motion` respected everywhere including the new §8.1
canvas animation, no horizontal scroll, 400px-viewport usability) —
restated as a hard requirement for every new surface this spec adds,
not a lighter bar for new work than existing work already met.

## 13. What this does not change

- No backend business logic beyond the two named schema additions
  (`admins.linked_practitioner_id`, `practitioners.
  accepting_new_clients`) and their obvious accompanying read/write
  routes — everything else in this spec is presentation, information
  architecture, and new client-side components, same category of
  change `v7`'s overview already established as the default.
- No change to Stripe/billing logic, to the retrieval/consult
  pipeline itself, or to any privacy/access-control enforcement
  (`v6.9`'s private-document model, `v6.5`'s client-record privacy
  scoping) — this redesign sits entirely above those systems.
- Legal page *copy* is not finalized by this spec (§8.5) — structure
  and placement only.

## 14. Implementation

Not detailed phase-by-phase in this document (the brief asked for the
spec first) — once reviewed, implementation follows this repo's
established discipline from `v7`: small, independently reviewable
PRs, each with its own `vX.Y`/`v8/0N-impl-*.md` note, nothing merged
without explicit confirmation. A reasonable first-pass ordering, for
discussion rather than decided here: (1) design tokens + Top Bar +
rail evolution, since every later phase depends on them; (2) the
account-linking schema change, since it's small and unblocks the
Users-page work; (3) Library's template-ification + the Graph view
rebuild, the highest-traffic surface; (4) the landing page rebuild +
legal pages; (5) practitioner Profile form + public directory
"accepting clients" surfacing; (6) Dashboard redesigns across all
three portals; (7) everything else.
