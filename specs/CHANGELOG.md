# Specs changelog

## 2026-11-05 — v15, library studio & tags window, multi-file uploads, graph overhaul, responsive mobile shell & consult AI briefing

See [v15/README.md](v15/README.md). Shipped comprehensive v15 feature suite and architectural reconciliation ([v15/11](v15/11-v15-system-drift-and-architecture-reconciliation.md)):
- **Library Studio & Dual-Window Organization**: macOS Finder-inspired studio window chrome (`.finder-toolbar`, dynamic collapsible `.inspector`, `.pathbar`). Introduced dedicated **Tags & Categories** organization window (`mainTab = 'tags'`) alongside `Folders` and `Graph` on the exact same dataset, treating topics as hierarchical folder categories (`category/subcategory`) with drag-and-drop categorization, untagged document bucket, and full category creation/rename/delete lifecycle.
- **Multi-File Uploads & Direct OS Ingestion**: Multi-file batch uploads supported across the "Add resources" modal dialog and native OS drag-and-drop directly onto sidebar trees, content areas, and breadcrumb crumbs.
- **Smart Placement Dialog & Persistent Notification**: Added interactive post-ingestion placement dialog with smart context suggestions (suppressing raw text inputs by default unless creating a new folder) and persistent toolbar notification bell (`.tb-placement-notify`) for deferred confirmations.
- **Concept Graph Physics & Visual Overhaul**: Spatial multi-graph separation prevents center clutter for disconnected components; 100% increased node spacing with click-to-separate radial blooming; data-volume-scaled node radiuses (60% reduced default base); interactive context minimap; glowing hover highlights for closest connected neighbors.
- **Responsive Mobile Navigation**: Shell upgraded with an adaptive mobile bottom navigation bar for high-priority shortcuts and a slide-over burger side drawer for the complete portal menu.
- **Practitioner Consult AI Opening Briefing**: Consultation sessions automatically synthesize and display an opening AI clinical briefing summarizing patient profile, intake responses, labs, and history strictly up to the consultation point in time.
- **In-Flight Ingestion Halting & Immediate Eviction**: Added right-click context menu and table action button controls to abort running background ingestion jobs (`POST /api/ingestion-jobs/{id}/stop`), evicting them from worker queues and purging staged assets immediately ([v15/13](v15/13-stop-ingestion-context-menu.md)).
- **Domain-Mindful Tagging & Concept Graph Quarantine**: Pre-classification pipeline segregates administrative and marketing files from clinical extraction, preventing practice business copy from polluting clinical knowledge graphs or misclassifying into medical specialty tags ([v15/15](v15/15-domain-mindful-tag-and-concept-extraction.md)).
- **Real-Time Maintenance Progress Streaming**: Dual-mode Server-Sent Events (SSE) streaming progress bar (`/api/maintenance/stream`, `/api/maintenance/status`) for Relink and Consolidate graph operations, with a sticky floating top progress banner across page reloads and an interactive modal controller ([v15/16](v15/16-relink-and-consolidate-progress-bar.md)).
- **Unified Multi-Select & Rubber-Band Drag for Folders & Categories**: Full 2D canvas rubber-band marquee multi-selection over documents, folders, and categories simultaneously, with modifier toggles (`Shift`/`Cmd`/`Ctrl`), itemized bulk context menus, and coordinated Move, Privacy, and Delete batch actions ([v15/14](v15/14-library-mouse-block-multiselect.md), [v15/17](v15/17-folder-and-category-multi-select.md)).
- **Library Icon & Folder Size Toggle**: 3-tier density switch (**Large** [default], **Medium**, **Small**) with dual-access controls (toolbar segmented pill with custom SVG sizing icons + canvas context menu), local storage persistence (`admin-library-icon-size`), and responsive multi-view CSS density adaptation across Icon Grid, List Table, and Miller Columns ([v15/18](v15/18-icon-and-folder-size-toggle.md)).
- **Late-Cycle System Drift & Architecture Reconciliation**: Formal reconciliation specification documenting architectural divergence between early assumptions and live implementations across ingestion, domain isolation, maintenance SSE, multi-selection, and visual density ([v15/19](v15/19-v15-late-cycle-system-drift-and-reconciliation.md)).
- **Responsiveness Bugs, Experience Gaps & Placement Real-Time Sync**: Fixed real-time desynchronization bug where deferred placement notifications persisted after document/folder deletion; added individual card dismissal in placement dialog; resolved modal viewport overflow via flex-column scrolling in `Dialog.svelte`; polished mobile layouts across library studio, public navigation hamburger alignment, consult chat thread stack, and file upload intake ([v15/20](v15/20-responsiveness-experience-gaps-and-placement-notification-fixes.md)).
- **Nature & Botanical Landing Pages Rebuild & Practitioner Flow Fix**: Rebuilt public landing and directory pages with an organic nature & leaves theme; preserved ambient falling leaves with emerald botanical palette; completely stripped all background boxes/tiles from the logo mark for a pure vector presentation; streamlined practitioner discovery with responsive clinical cards, a 3-stage care timeline, and a dedicated provider platform section; overhauled "For Practitioners" (`/join`) into an extensive guidance hub; guaranteed clients never see AI by positioning intelligence as a behind-the-scenes copilot so no information is missed; purged "herbal" phrasing in favor of functional medicine and peer-reviewed literature; codified practitioner sovereignty over client-specific phased protocols (practitioner decides what is implemented and when); added `protocol` entry kind to clinical vault and patient context; harmonized public CSS and theme tokens across all public pages ([v15/21](v15/21-botanical-landing-pages-and-practitioner-flow-rebuild.md)).

## 2026-11-05 — v14, settings agent models, token analytics & chart overhaul

See [v14/README.md](v14/README.md). Overhauled the usage charts and admin Settings page: replaced the crude 64px sparkline with a professional, interactive SVG chart component (`UsageChart.svelte`) featuring smooth Bézier curves, gradient area fills, formatted axes, and hover crosshair tooltips. Added comprehensive per-agent tracking across all 6 AI team roles (Reader, Graph Builder, Embedder, Answer Engine, Reasoner, Checker), surfacing assigned models, providers, and prompt/completion token spend in both Table and Graph views controlled by a toggle.

## 2026-11-05 — v13, private-route redesign

See [v13/README.md](v13/README.md). Redesign the admin/practitioner/client portals following app CSS conventions: tokens in `app.css` under `.portal` and `.portal-{role}` (no `surface.css` override file), per-role palettes (Nordic teal for practitioner, midnight indigo for admin, berry rose for client), falling leaves on the rail, floating rounded-canvas shell (`.portal-main`), unified `.detail-head` header across all pages including Library, modern compact right-click context menu, and polished modal dialogs.

## 2026-11-05 — v12, private-route (dashboard) repaint

See [v12/README.md](v12/README.md). Direct instruction: the admin, practitioner and client portals looked stale; repaint to a modern, professional look. Token-driven and scoped to `html[data-surface='app']` so public routes are unchanged: solid surfaces (no glass), new slate sidebar with user card, white page header, card-based home pages, boxed inputs with focus ring, per-portal accents (rose / teal / indigo).

## 2026-11-05 — v11, landing page + public nav redesign

See [v11/README.md](v11/README.md). Direct instruction: redesign the
landing page, with copy about professional practitioners who, helped
by AI tuned only to a knowledge base, can help more — client-facing
copy first, practitioners second. The old hero and trust-pillars
section were written in the practitioner's voice; rewritten client-
first, with a new dedicated "For practitioners" section near the end
carrying the "help more" pitch directly to practitioners instead of
interleaving it earlier. Added three new SVG illustrations (a
knowledge-graph motif, a grounded/verified-book motif, a practitioner-
plus-AI motif) in a new `web/src/lib/components/art/` folder, drawn in
the same stroke-and-soft-fill style the existing icon set already
uses. Redesigned the navbar: an underline-wipe link hover, and —
direct instruction — the logo mark no longer sits in a background box
(it was in a red one). Also relabeled the client-signup CTA from a
generic "Get started" to "Sign up as a client," after a live report
that the client path through the site, while real, wasn't named
anywhere a visitor could see it.

## 2026-11-05 — v10, production drift against v9's codebase-only picture

See [v10/README.md](v10/README.md). Implementing v9's candidates A
(Anthropic prompt caching) and B (parallelize the ingest Reader call)
and investigating candidate F (raise `INGESTION_CONCURRENCY`) per
direct instruction meant SSHing into the production VPS for the first
time this spec series has done that, rather than reasoning from the
codebase alone. Three things didn't match what the code implied:
candidate C's "formalize the local embedder" framing was already
half-wrong (`EMBEDDER_FORCE_LOCAL=true` is already the live, deliberate
production config, not a fallback default waiting to be flipped — and
Nebius's embeddings endpoint is still returning `402 insufficient_quota`
on a direct test, so there's no live "choice" being made at all right
now); candidate F's real constraint is the VPS itself (2 vCPUs, a
single gunicorn worker serving all live traffic, embedding already
CPU-bound local inference) rather than anything in the code, and is
recommended against on this box; and two minor operational loose ends
(a stale `clinic.service.bak` unit file, no git checkout on the deploy
box) were found and recorded, not fixed. A and B are implemented and
deployed to production, verified via a clean graceful reload and a
healthy health check.

## 2026-11-04 — v9, backend pipeline latency brainstorm (spec only, not implemented)

See [v9/README.md](v9/README.md). Direct request: make the backend AI
pipeline (ingest + consult) at least 30% faster, same-or-better
accuracy, free tools only, same API contract where one exists — "find
the best one" rather than build several. Read the real ingest/retrieval/
reasoning call sequence end to end before proposing anything (no
guessing), found five real candidate levers, and recommends a combined
package of the three that are free, zero/near-zero accuracy risk, and
need no API-contract change: Anthropic prompt caching on every role's
static system prompt (production is currently on the Anthropic
provider, confirmed live, and implements no caching today), running the
ingest Reader call concurrently with chunking+embedding (independent
work currently run sequentially for no reason), and formalizing the
already-live local embedder (currently only an undocumented emergency
fallback, active in production right now because of a past Nebius
billing outage) as the deliberate default. Spec only, per instruction;
implementation needs a live before/after timing run to actually claim
the 30% target, not an estimate.

## 2026-11-04 — v8, full UX/UI redesign (implemented, live-verified in production)

See [v8/README.md](v8/README.md). Direct request, assembled from a
rapid sequence of messages treated as one combined brief: redesign
layout and UX across the whole app (keep only color/branding), rebuild
the Graph view lightweight, rebuild the landing page with animation and
a practitioner highlight, support an optional admin↔practitioner dual
role, add EU legal/disclaimer pages, and build out the practitioner
profile page's forms. Spec first (one single file, per explicit
instruction overriding the v7-style multi-file convention), then
implemented in one pass on explicit follow-up instruction ("implement
them all, do not ask me for phases"). Shipped via PR #103, merged and
deployed, health-checked live.

## 2026-11-04 — v7, full UI/UX redesign (spec only, not implemented)

See [v7/README.md](v7/README.md). Direct request: redesign the whole
app — landing page and all three portals — to be interactive, user-
friendly, modern, and professional. Per explicit instruction ("create
the specs first, do not implement"), this is scoping/design
documentation only — nothing built. User's explicit choices: all four
surfaces in one combined spec (not staged by surface), keep the
current brand/palette and modernize execution rather than rebrand, and
prioritize micro-animations/transitions, onboarding/guided flows, and
a command palette as the interactivity additions. 8 files: an
overview, design-system foundations, one spec per surface, a
cross-cutting interactivity spec, and an 8-phase implementation plan
(design system → landing page → admin Library → rest of admin →
practitioner → client → command palette → onboarding), each phase its
own independently reviewable/deployable PR per this repo's existing
norm.

## 2026-11-04 — v6.20, Library sort, concepts-stat bug fix

See [v6.20/README.md](v6.20/README.md). Sort by name/date-ingested
across every document view; checked the data model before adding a
third "date uploaded" option and found no second timestamp exists to
back it (a document's upload and ingest times are the same fact in
this system). Also fixed a real pre-existing bug found live: the
Library tab's "N concepts" stat read a field name `store.graph_stats()`
never actually returns, silently showing 0 regardless of the real
entity count since the line was first written.

## 2026-11-04 — v6.19, local-embedder OOM fix, menu reliability rewrite

See [v6.19/README.md](v6.19/README.md). Two live production incidents:
a 502-causing OOM crash loop, root-caused via `journalctl`/`dmesg` to
`LocalEmbedderClient.embed()` running an entire large book's passage
list through one unbatched CPU forward pass (fixed: batched at 32,
independent of the ingestion queue's own concurrency cap, which was
not the actual cause despite being the natural first suspect given
prior OOM history); and `Menu.svelte` rewritten off the native
`popover` attribute onto explicit Svelte state after a live report it
didn't open on click — it now gates core per-document actions across
every Library view, so removing any dependency on Popover API browser
support was judged worth the extra code.

## 2026-11-04 — v6.18, Graph view visibility/sizing/perf/zoom controls

See [v6.18/README.md](v6.18/README.md). Four pieces of direct/live
feedback on the Graph view in one pass: edges that existed in the data
but were rendered with a near-invisible stroke color (not a missing-
connections bug), oversized nodes, no visible scroll/zoom affordance
(added explicit controls + a scrollable container), and real browser
performance cost from unconditional stroke-outlined text labels —
fixed with zoom/hover-gated label rendering past a 60-node threshold,
plus lowering the concept layer's default node limit 150→80.

## 2026-11-04 — v6.17, Table view action parity

See [v6.17/README.md](v6.17/README.md). Closes the single largest gap
`v6.16`'s PM+QA audit deferred: Table view's row actions were View/
Move/Delete only, with no private/public toggle, Edit access, or
uploader assignment, and no visibility into the in-progress ingest
queue at all. Now uses the same "⋮" Menu as Icons/List, a private-doc
lock badge, and staged-item rows with progress/Retry/Discard.
## 2026-11-04 — v6.16, PM + QA audit (two parallel subagents), fixes

See [v6.16/README.md](v6.16/README.md). User asked for a PM pass and a
QA pass over everything shipped today as separate subagents, run in
parallel with no visibility into each other, then reconciled. Highest-
severity QA finding: a double-ingest race (no backend guard against
two jobs for the same staged item) that could report a genuinely
successful ingest as a failure. Also fixed: the Graph view's own
`v6.15` centering fix being itself buggy for large graphs, a blank
search dead-end, folder-move path corruption on move-to-root, a
missing `invalidateAll()`, audit-log entries for nonexistent-document
edits, dead "Kind" filter chips, missing Graph-tab stats, and
undifferentiated concept-graph node colors. Real findings from both
passes were deferred rather than fixed — see `01`'s "Deferred" list,
headlined by Table view's missing action parity with Icons/List.

## 2026-11-04 — v6.15, retry all, graph centering, nav bug, card polish

See [v6.15/README.md](v6.15/README.md). Four pieces of direct/live
feedback: a bulk "Retry all" for the errored-queue-item backlog; a
real root-cause fix for the Graph view not fitting its own viewport
("a mess"); a real bug found in the shared nav rail (`AppRail.svelte`)
where the admin Library item showed as active on every admin page, a
plain prefix-match bug now fixed generally (most-specific-href wins);
and doc-card density/clarity polish (author vs. uploader now visually
distinct by icon and color, tags/forms tightened).

## 2026-11-04 — v6.14, doc-card "⋮" menu, uploader claim/assign

See [v6.14/README.md](v6.14/README.md). Two direct requests: tidy the
doc-card's 5-6 always-visible action icons into a "⋮" dropdown (new
`Menu.svelte`, native `popover`), and let an admin assign who uploaded
a document. Checked the audit log before building the second one —
every "ingest" event's actor is hardcoded to the literal string
"admin" (verified live: 21/21), so there's no real history to backfill
from; shipped as a manual claim/assign instead, per the user's choice
when told that.

## 2026-11-04 — v6.13, knowledge-base graph view

See [v6.13/README.md](v6.13/README.md). Direct request, user chose
"both, as switchable layers" when asked which the graph should show.
New Graph view tab: document/folder layer (client-side, reuses the
Tree view tab's data) and concept layer (the actual typed-relationship
knowledge graph, bounded to the top 150 entities by relationship
degree — production has 7905+). Added `d3-force`/`d3-drag`/`d3-zoom`/
`d3-selection` as dependencies — checked `force-graph`'s own dependency
tree first and chose the four focused d3 primitives over it.

## 2026-11-04 — v6.12, removed the staging/review step

See [v6.12/README.md](v6.12/README.md). Direct request: no more
separate "Staged for review" tab or manual "Ingest" click — every
upload auto-queues immediately, shown as a progress-bar card right in
the Library grid, with a server-side status bar (counts, chars queued,
ETA) and a finalize bell instead of the old auto-popped placement
dialog. Found and fixed a real bug along the way (`'queued'` jobs
invisible to `GET /api/ingestion-jobs/active`) and a real prod backlog
(17 pre-existing staged items, most errored from the Nebius billing
exhaustion) that the new "every staged item shows its real state"
design had to account for rather than assume away.

## 2026-11-04 — v6.11, Library tree-view tab, icon-drift/placement-UX fix

Three separate pieces of direct/live feedback, shipped as three PRs:

- **Tree view tab** (`v6.8/01` addendum) — a new admin Library tab
  showing folders and documents together as a unified tree, defaulting
  to 3 levels deep with a chevron to go further. Built entirely from
  already-loaded `data.sources`/`data.folders` (no new fetch), to meet
  an explicit "<100ms load" requirement.
- **Icon drift + post-ingest placement UX** (found live, with a
  screenshot) — a long doc-card title wrapping into many short lines
  next to the always-visible action icons, stretching the card and
  pinning the icons to its top; fixed with a 2-line clamp + ellipsis.
  Also: finishing an ingest now opens a "Placed in library" dialog
  showing the Reader's suggested folder/tags (editable in place), and
  the completion toast now names where the document landed.
- **`v6.11` — document metadata + view modes** — see
  [v6.11/README.md](v6.11/README.md). A real gap-check against live
  feedback: tags already worked, but content-type classification,
  author display, and "who uploaded this" all turned out to be genuine
  gaps, not just hidden UI — confirmed by reading the ingest pipeline
  rather than assumed.

## 2026-11-03 — admin portal polish, tags, folder tree, HHEM removal

A batch of direct requests, no new spec version (maintenance/UX on
already-shipped features, not new scope):

- **Real folder tree UI** (`v6.8/01` addendum) — the flat folder chip
  row replaced with a real nested, collapsible tree sidebar
  (`FolderTree.svelte`), drag-and-drop to move a document onto a
  folder, prefix-match filtering (select a folder, see its subfolders
  too).
- **Editable tags** (`v6.8/01` addendum) — topics are now admin-
  editable/assignable per document (add/remove chips), not just a
  Reader suggestion frozen at ingest time. New `store.set_topics()` +
  `PATCH /api/sources/{id}/topics`.
- **System health moved to a footer status bar** — the dashboard's
  per-role chip block replaced with a compact, persistent dot-per-check
  bar at the bottom of every admin page (`(admin)/admin/+layout.svelte`),
  hover for the ms/error detail a chip used to spell out.
- **Fixed**: `/api/health`'s embedder check reported "down" with an
  `AttributeError` whenever `EMBEDDER_FORCE_LOCAL` was on —
  `ping_role()` used to reach into `client._client.models.list()`
  directly, which only the openai-SDK-backed client has.
  `LLMClient`/`AnthropicLLMClient`/`LocalEmbedderClient` each gained
  their own `.ping()` now, and `ping_role()` just calls it.
- **Removed**: the local HHEM-2.1-Open anti-hallucination classifier
  (`app/reasoning/checker.py`, `cfg.checker_model`/`checker_threshold`)
  — confirmed unused in the real consult pipeline (`llm_checker.py`'s
  LLM-as-judge has been the active path since `v6.3`); removed outright
  rather than left as dead code. `transformers`/`torch` stay in
  `requirements.txt` for the local embedder fallback, which needs them
  independently.
- Admin rail: Dashboard and Library swapped order (Dashboard first).

## v6.10 — 2026-11-02 (practitioner-owned private knowledge base)

Any Pro practitioner — not just one an admin has flagged with
`can_upload_library` — can upload documents that become part of their
own consults immediately, private to them alone, no admin step. Reuses
`v6.9/01`'s `is_private`/`document_access` enforcement exactly
(nothing new in the retrieval paths), just automated at ingest time:
the uploading practitioner grants themselves access instead of an
admin granting it afterward. Adds `Document.owner_practitioner_id` —
the provenance tag found missing while reading `app/main.py`'s staged-
upload code (`owner` already exists, but only as bookkeeping on the
transient `staged_sources`/`ingestion_jobs` tables, never written onto
the resulting `Document`). A new, parallel set of routes
(`/api/me/knowledge/stage*`, `DELETE /api/me/knowledge/{id}`) rather
than a flag on the existing `can_upload_library`-gated ones, so that
permission's meaning doesn't change. Diverges from the shared-library
path on folder suggestion (skipped) and deletion (the owning
practitioner can delete their own via the new route). Found and closed
in review: the new personal-ingest route's `replaces` parameter is
now checked against document ownership before deleting — the existing
shared-library promotion route has the same shape with no equivalent
check, a pre-existing gap flagged but out of scope to fix here. The
admin-Library "Owner" facet from the spec (to keep personal uploads
from diluting the default shared-library view) is not yet built — the
backend tag (`owner_practitioner_id`, already on every `_CARD`
response) is there for it when that UI lands.

## v6.9 — 2026-11-02 (private knowledge base, per-practitioner access)

Admins can mark a document — or a whole folder (`v6.8/01`) at once, via
bulk-select — as private, invisible to every practitioner's RAG results
except the specific ones explicitly granted access. A new core-store
`document_access` table (admin-controlled, so it does not live in a
per-practitioner vault schema the way `source_weights` does). Enforcement
has to cover three separate retrieval paths a private document could
otherwise leak through: seed search, every graph-traversal hop, and the
general-lookup pgvector fast path. States explicitly that "privatize a
folder" is a one-time bulk action, not a persisted folder-level policy —
the same tradeoff `v6.8/01`'s string-prefix folder model already accepts.

## v6.8 — 2026-11-02 (library folders; citation deep-link)

Two direct feature requests. `01` (folder/subfolder organization over
the knowledge library, `Document.folder_path` as a plain string prefix
— not a separate node type — with the Reader suggesting a path the same
way it already suggests topics; the admin's placement is always final)
is implemented: `app/graph/store.py`/`app/ingestion/pipeline.py`/
`app/main.py`, plus a folder facet row, per-card folder field, and a
rename action on the admin Library page, and a read-only folder column/
filter on the practitioner knowledge page. `02` (clicking a citation on
a generated answer opens the library in a new tab at that exact document
and passage/page) is also implemented: the admin and practitioner
library viewers were promoted from client-side dialogs to real routed
pages (`/knowledge/[id]`, `/admin/[id]`), each taking a `?locator=` that
scrolls to and highlights the exact passage, or opens a PDF at the exact
page via `#page=N`. Admin/superadmin CRUD on accounts and the
practitioner library viewer this builds on both already shipped (`v6.6`,
`v6.7`) — noted as baseline, not re-specced.

## v6.7 — 2026-09-16 (SEO/GEO; practitioner-owned questionnaires; portal UX batch)

Same day as `v6.6`'s audits, a run of direct feature/UX requests.

SEO/GEO: the public pages had only a bare `<title>` — no meta
description, canonical, Open Graph/Twitter tags, structured data,
sitemap, or llms.txt. Added a shared `Seo.svelte` (indexable content
pages get real descriptions; pure utility pages are `noindex`),
`Organization`/`Person` JSON-LD, a branded OG image, `sitemap.xml`
(prerendered, enumerating every practitioner), and `robots.txt`/
`llms.txt` for GEO (explicitly naming GPTBot/ClaudeBot/PerplexityBot/
etc., since that's the convention those crawlers look for even though
the existing blanket allow already covered them). Found and fixed the
same day: the three new root-level static files were being served as
the SPA shell instead of their real content — `app/main.py`'s
`_WEB_ROOT_FILES` allowlist didn't know about them.

Practitioner-owned questionnaires: previously one global admin-curated
questionnaire, shared by every practitioner's clients. Added
`questionnaires.practitioner_id` (NULL = admin default), scoped the
"only one active" invariant per-owner instead of globally, and added
explicit activate/deactivate (previously only implicit via creating a
new version). New practitioner-facing builder (Pro-only), mirroring the
admin one. Same-day follow-up request: practitioners can view the site
default (read-only) alongside their own, not just their own. A
`/code-review` pass before shipping caught a real gap: the auth check
backing the new practitioner library-source viewer (below) initially
let *any* practitioner through, not just Pro accounts — tightened
before merge.

Portal UX batch: notification badges on the practitioner nav (unviewed
intake, new contacts — both already tracked server-side, just not
surfaced) and a per-client marker on the Clients list; practitioner and
client portals drop their `.container` width cap (public pages
untouched, consistent with `v6.6/03`'s gutter-fix-then-revert there);
practitioners gain a real library-source viewer (text or original PDF),
not just weight adjustment; admin/practitioner/client dashboards gain
real quick-action tiles instead of raw stat dumps or static copy
(client dashboard's Health record tile didn't exist before — that
feature, `v6.5`, had no dashboard entry point at all); icons extended
from admin-only (`v6.6/03`) to practitioner and client action buttons
too.

**Why:** all of this was requested directly by the user across a single
session, not found incidentally — SEO/GEO, then questionnaire ownership,
then a rapid sequence of portal-polish requests (badges, width, library
viewer, dashboards, icons) that landed together since several touch the
same practitioner-layout file.

## v6.6 — 2026-09-16 (client and superadmin portal audits; public-page layout)

Two structured "act as a real user" audits run against the live app.

Client-portal audit: the wearables page showed a plain "Connected" chip
and a "N connected" dashboard count indistinguishable from a real
integration, even though `app/wearables.py`'s own docstring says
post-connect data is fixture, not a live vendor pull — fixed with an
honest "Coming soon" state (backend OAuth plumbing untouched). The
questionnaire page ignored its own typed schema (text/number/date/
choice/multi_choice, options, theme) and rendered every question as a
plain textarea — fixed with type-aware inputs, theme grouping, and a
progress bar. One finding left open, pending a product decision: a
client has no visibility at all into what their practitioner discussed
or decided via the AI consult tool.

Superadmin-portal audit: a real Postgres `audit_events` trail was being
written on every sensitive admin action (practitioner approve/reject/
suspend, admin create/role-change/suspend) with no endpoint or page
ever reading it back — fixed with a paginated read endpoint and a
second Audit-page section. Admin-account and client-account management
both existed on the backend with zero UI — both fixed, the Admins tab
now also gated to `session.admin_role === 'superadmin'` on the
frontend since a plain admin could otherwise see fully-interactive
controls that just 403'd. **A real auth-enforcement gap was found while
wiring up client suspension**: `app/auth.py`'s client login path and
`require_client` never checked any active/suspended flag for the
client themselves (only for their practitioner) — a suspended client
could still log in, and an already-logged-in one kept full access
until their session cookie expired. Fixed with a live DB check on every
request, the same pattern already used for admin role enforcement.
Also fixed: a questionnaire-builder bug that silently flattened typed/
themed questions to plain text on every edit; a missing health-status
panel on the admin dashboard; a practitioner-table search box and
client-count column; UI triggers for the previously curl-only
`/api/relink` and `/api/consolidate` maintenance routes.

A separate, unrelated fix — the public navbar and practitioner-
directory grid were capped at the same 78rem reading-width used for
actual body text, reading as dead margins on wide screens — was shipped
same day, then reverted at user request a few hours later. The
implementation approach (and a CSS-specificity pitfall hit and fixed
along the way) is kept in `v6.6/03` for reuse if wanted again; the live
site is unchanged from before this entry on that specific point.

**Why:** both audits were requested directly ("act as a user/client...
identify the gaps", then the same for superadmin) rather than found
incidentally — a deliberate sweep for gaps neither user-reported bugs
nor code review had surfaced yet.

## v6.5 — 2026-09-15 (lab intake; three-deployment model routing; consult page hardening)

Lab intake: practitioners and clients can both record patient data
(labs, conditions, medications, notes, history) — `get_patient_context()`
had read these fields since it was written, nothing ever wrote them.
Privacy-scoped: a client only ever sees/deletes their own self-reported
entries, never a practitioner's private notes about them.

Model routing spread across three deployments: a dedicated Qwen3-32B
endpoint (Reader/Graph-builder/Checker-LLM), Kimi-K3 routed to Nebius's
EU-west2 region (Reasoner/Answer Engine — the only model that region
serves at all), a dedicated Qwen3-Embedding-8B endpoint. Two real
compatibility bugs found and fixed: the dedicated Qwen3 deployment
needs a different thinking-disable mechanism than Kimi (and inlines
its `<think>` block in a way that would've broken strict JSON parsing
outright), and its `max_tokens` ceiling is far lower than the shared
catalog's. Kimi-K3 confirmed consistently slower than Qwen3-235B in
paired live trials — a deliberate residency-vs-speed tradeoff, not an
oversight.

Three consult-page bugs found and fixed live: `general_lookup`'s "How
it searched" dumping the full conversation history instead of the
actual question; auto-selecting the first client and losing the
selection on refresh; and a real regression from fixing that —
the sidebar going entirely unclickable on first arrival, caused by an
uncaught error inside a `$effect` breaking the rest of the component's
reactivity. See [`specs/v6.5`](v6.5/README.md).

## v6.4 — 2026-09-14 (consult page as a chat interface; hallucination fix)

Consult page rebuilt as a GPT/Claude-style chat interface — persistent
sidebar (searchable clients, calendar-badge conversation history, a
patient info widget), a bottom-pinned composer, markdown rendering, a
closed-by-default sources accordion, a mode toggle. Two live UI bugs
found and fixed along the way (a CSS grid/flex overflow, 0-turn ghost
sessions in the history list).

Also a real hallucination bug, found live: a question about bloating
got an answer built from topic-adjacent context that never actually
covered it. Fixed in the Reasoner's system prompt (explicit: topic-
adjacent isn't "covers the question"), verified live. Also fixed two
citation-parsing bugs found while verifying it — an inflated `sources`
list, and grouped citation brackets (`[K1, K3]`) silently missed by
both the server- and client-side citation matchers. See
[`specs/v6.4`](v6.4/README.md).

Same day, separate change: the Checker got a small-LLM-as-judge
alternative (`app/reasoning/llm_checker.py`), replacing the local HHEM
classifier as the default — 1.2-6.5s/call verified live, versus HHEM's
28-77s. `run_check` is back to `true` by default. See
[`specs/v6.3`](v6.3/README.md).

## v4.2 — 2026-09-09 (library directory browse; ingest modal; Library/Staged tabs; full-document grading)

Same day as `v4.1` below, later still — a run of follow-ups to the
DMOZ-style library request from earlier the same day, detailed in
[`specs/v4/05-post-launch-additions.md`](v4/05-post-launch-additions.md#library-browse-the-ingest-modal-and-a-librarystaged-tab-switch):

- **Ingest is now a modal**, not a permanent rail panel: a "+ Add
  resources" button on the library opens the upload/paste/scrape tabs in
  a `Dialog` (which gained an optional `wide` variant), closing itself
  automatically once staging succeeds.
- **Library browse redesigned as a directory**: with no search and no
  category picked, the library shows a grid of category tiles (one per
  `Topic`, with a document count) instead of an inline chip row —
  matching the https://dmoz-odp.com/ shape referenced in the request.
  Picking a tile (or typing a search) swaps to a breadcrumb, a Kind
  facet row standing in for "subcategory," and the results table. Same
  caveat as the original DMOZ pass: Neo4j has no real category hierarchy,
  so this is a presentation change over the existing flat `Topic`/`Kind`
  facets, not a new data model.
- **Library and Staged are now tabs of one panel** (with a live count on
  the Staged tab), replacing an intermediate cut that had split them
  across the rail and the main column. Fully separates the two action
  lists — Ingest/Discard (staged) vs. Regrade/Remove (library) — that
  this page kept getting reported as confusing when they sat next to
  each other.
- **Reader grading now reads the whole document**: the `text[:20000]`
  cap that H8 (see `v4` entry below) had only made *visible* is now
  removed outright, at explicit request ("read them all, no partials").
  `truncated`/`reader_truncated` is gone end to end — `llm.py`,
  `knowledge.py`'s write/read, `main.py`, and the admin chip — since the
  condition it flagged can't happen anymore. Tradeoff: a source whose
  text exceeds the Reader model's context window now fails ingest
  outright instead of silently grading a partial read; not yet hit in
  practice.
- **Bug fix**: the audit-log preview on the Knowledge page read
  `a.created_at`, a field `AuditEvent` nodes never had (the real one is
  `a.ts`) — every row rendered as `"{action} — "` with nothing after the
  dash.
- **Audit history moved to its own page** (`/admin/audit`, new AppRail
  nav item), showing every returned event (Who/Action/Detail/When) in a
  real table instead of a hardcoded 6-row preview wedged into the
  Knowledge page's rail. Fixes the bug above in the same pass, since the
  rendering code moved wholesale.
- **Admin layout now uses the full content width**: dropped the shared
  `.container` (`max-width: 78rem`, tuned for the public site's prose
  pages) from the admin shell only, after it left growing empty gutters
  on the Knowledge page's directory grid and tables on anything wider
  than a laptop.

## v4.1 — 2026-09-09 (CI/CD, chunked uploads, staged-source review queue, layout fixes)

Same day as the `v4` entry below, later in the day — three unrelated
pieces of post-launch work, detailed in
[`specs/v4/05-post-launch-additions.md`](v4/05-post-launch-additions.md):

- **Automatic deploy**: pushing to `main` now builds, syncs, and restarts
  the service automatically (`.github/workflows/deploy.yml`), gated by a
  Python-syntax + `npm run check` job. A PR into `main` runs that same
  check for review signal, but the deploy step itself only ever runs on
  an actual push to `main`.
- **Chunked upload, up to 200 MB**: `app/uploads.py` streams a large file
  to disk in pieces instead of buffering the whole thing in memory —
  `clinic.service` caps the process at 500 MB, and Neo4j's JVM already
  takes most of what's free. Used by both admin source ingest and client
  file upload; the existing 20 MB single-request routes are unchanged,
  kept for small files and API/script callers.
- **Staged-source review queue**: builds
  [`specs/v3/18-document-ingest-upgrade.md`](v3/18-document-ingest-upgrade.md)'s
  "staged uploads" in full — written, never implemented until now.
  Upload (drag-and-drop, with a live PDF preview), paste text, or enter a
  URL to scrape; each lands in a reviewable staged list (no Reader call,
  no Neo4j write yet), then ingest all selected at once or one at a time.
  Stores page-structured text (not the flat text column the original
  spec proposed), so a staged PDF keeps real per-page citations after
  promotion. The scrape path fetches the page, strips markup, then runs
  a bounded Haiku extraction pass whose only job is discarding chrome —
  navigation, headers, footers, ads — never summarizing or rephrasing
  the content it keeps.
- **Layout**: a shared rail-plus-main-column CSS utility, fixing
  single-column stacking on the admin Knowledge page (flagged directly
  as "annoying to look at"), the practitioner Dashboard, and the
  practitioner client-detail page.
- **Bug fix**: the admin Knowledge page's graph-stats line
  (`data.graph.node_count`/`edge_count`) read field names that don't
  exist on `GET /api/graph`'s real response — always showed 0 regardless
  of the graph's actual state. Fixed to read the real fields
  (`concepts`/`mentions`).

## v4 — 2026-09-09 (post-deploy fixes: PM/QA/Clinician review, 42 of 44 findings fixed)

Same shape as [v2.1](#v2.1)'s precedent: corrections made after `v4` (the
SvelteKit rewrite) went live (commit `5e0c14f`, 2026-09-02), tracked here
rather than waiting for `v4/` to be formally cut as the current version per
[specs/README.md](README.md)'s own versioning rule — that cut still hasn't
happened; [`specs/v4/04-known-issues.md`](v4/04-known-issues.md) flags it
explicitly as a separate, unresolved process gap.

A PM/QA/Clinician-lens code review of the full deployed app (`app/` +
all four SvelteKit portals) produced
[`specs/v4/04-known-issues.md`](v4/04-known-issues.md) — 9 Critical, 12
High, 18 Medium, 5 Low findings. 42 fixed same-session, each its own
commit; M7 was retracted on closer check (it matches
[specs/v2/03-website.md](v2/03-website.md)'s spec, not a bug); M18
resolved as a side effect of C9's fix; M1 only partly fixed. Full detail,
including exact file:line references and what each fix does, lives in the
findings doc itself rather than duplicated here.

**Critical (live security/access-control defects, or a flagship feature
completely non-functional):** an unapproved/rejected practitioner could
pay for and use Pro features before admin review; the anti-hallucination
verdict badge always showed the wrong state; citations were captured by
the backend but never rendered — the `[S1]`/`[S2]` markers were dead text;
a flagged ("weak"-verdict) answer reached the permanent patient record
with no trace it was flagged; a practitioner's personal source down-weight
was bypassed during graph traversal; self-serve client signup always
400'd — the site's primary conversion path could never complete;
unauthenticated practitioner-signup photo upload had no validation
(stored-XSS risk); switching clients mid-consult could attribute one
patient's answer to another with no label; a demoted superadmin kept
elevated access for up to 12h (stale session, not re-checked live).

**High:** the admin library lost its delete/regrade UI in the rewrite;
uploaded client files could never be opened again by anyone; Stripe
redirects pointed at retired pre-rewrite pages; multi-turn consult history
never actually carried forward (every question started a new session) and
deep-linked past sessions weren't replayed; an unset
`VAULT_ENCRYPTION_KEY` silently corrupted stored API keys across a restart
with no fail-closed check; "save session summary" had no UI entry point;
non-PDF/non-text uploads were silently ingested as garbled "sources"
instead of rejected; long sources were graded from a truncated read with
no indication; no password-strength check at any account-creation path;
the librarian's reasoning was captured but never shown; no login rate
limiting; a consult-stream failure only surfaced for one exception type.

**Medium:** suspended/rejected practitioners' contact form and admin
re-approval path; a failed consult left its progress UI stuck "running";
no way to cancel a consult stream on navigate-away; questionnaire editing
had no UI; wearable connections had no disconnect; client file-upload
errors were swallowed to a generic message; unbounded `per_page`; a few
unhandled-exception-to-500 gaps (profile field parsing, `_json_call`,
blank consult questions billing the full pipeline); dashboard tiles using
emoji icons / static copy instead of the shared `Icon` component and real
status; Pro-gated nav items not marked as gated; a self-flagged filter
bug in this same review's own admin-library redesign; a transient
logged-out nav flash.

**Low:** an inconsistent post-login redirect fallback; no email-format
validation; an inconsistent destructive-action confirmation pattern
(native `confirm()` vs. the app's `Dialog` vs. none); dead `type="submit"`
markup; a questionnaire-submit page not refreshing its own persisted state.

## v3 — 2026-08-17 (bounded AI-answer revision, reachable Summariser, Material Design 3) {#v3}

Prompted by "can we make the agents talk to each other?" A three-agent
(PM/Analyst/Architect) review of the seven-role AI pipeline
([07](v3/07-ai-team.md)) concluded general agent-to-agent messaging isn't
warranted — the fixed pipeline's auditability (each role's input/output is a
reviewable code-level contract, e.g. the Librarian is structurally blind to
source grades) is the actual product value, and a framework like LangGraph
or CrewAI would be disproportionate for seven plain functions in one file.
It did find one real gap, one orphaned feature, and a few security items,
all closed here:

- **Bounded Checker → Specialist retry** ([07](v3/07-ai-team.md),
  [08](v3/08-api.md)): a `weak` verdict previously went nowhere — the flawed
  answer shipped with a badge and the Checker's own `unsupported` list was
  never acted on. Now triggers exactly one revision attempt, hard-capped in
  the route handler, never left to the model to extend.
- **Summariser reachable**: fully implemented since v1 (`summarize_session()`
  in `app/llm.py`, a `session_summary` vault entry kind), never wired to a
  route — an orphaned feature, not a deferred one. New `POST
  /api/me/clients/{id}/sessions/{session_id}/summary`.
- **Error handling added to the consultation path** — previously the only
  LLM call site with no try/except; an Anthropic API failure now returns a
  structured 502 instead of an unhandled exception.
- **Two hardcoded fallback secrets fixed**: `session_secret` and
  `neo4j_password` in `app/config.py` silently defaulted if unset, the same
  failure shape already documented for `VAULT_ENCRYPTION_KEY` but not
  itself flagged until this review. Both now fail closed in production
  ([10](v3/10-security.md)).
- **HTTP `QUERY` method**, experimental: adopted on three filter-heavy read
  endpoints (practitioner directory, admin roster, library source search),
  `POST` kept as fallback since it's a still-draft HTTP method not yet
  universally proxied ([08](v3/08-api.md)).
- **Material Design 3**, via Google's `@material/web` component library —
  this project's first real external dependency and first build step
  (`npm` + Vite, [11](v3/11-operations.md#build-step)). Presentation-layer
  only: no information architecture changed, so [03](v3/03-website.md)
  through [06](v3/06-client-portal.md) carry forward from v2 unedited. See
  [15 · Design system](v3/15-design-system.md) for what's replaced (buttons,
  fields, menus, dialogs, snackbars, chips) and what isn't (the sidebar
  shell, kept hand-built and re-themed).

- **Live agent-progress toast**: `POST /api/me/consult` becomes an SSE
  stream reporting which of the seven roles is currently running and a live
  cumulative token count (from the Anthropic response's real `usage`
  figures, not an estimate), rendered as a persistent `md-snackbar` during
  the request ([08](v3/08-api.md#live-progress-stream),
  [15](v3/15-design-system.md#live-agent-toast)). Granularity is per-agent-
  call, not per-token — true token-by-token would mean switching every role
  to streaming completions, out of scope here.

**Explicitly deferred**, real findings from the same review not bundled into
this release: a Librarian empty-result fallback UX (suggest broadening the
grade threshold, nudge an admin to add a source), and a Reader/Indexer
shared-context pass to reduce topic/concept vocabulary drift. See
[v3/TODO.md](v3/TODO.md) for the full sequencing and everything still open
from v2.

## v2.14 — 2026-08-14 (responsive/overflow fixes; password visibility toggle; login validation; consultation-list polish)

- **No horizontal overflow, site-wide.** Added a global guard
  (`html`/`body { overflow-x: hidden }`, `overflow-wrap: break-word`,
  `img/svg/video { max-width: 100% }`). Found and fixed the actual bug
  behind two layouts not collapsing on narrow screens: `consult.html` and
  `client-detail.html` set `grid-template-columns` via an inline `style=`
  attribute, which always wins over a stylesheet rule regardless of
  whether its `@media` query matches — so the existing mobile-collapse
  rules never applied to them. Replaced both with classes
  (`.workspace.overview-right`, `.split-rail`) that carry their own
  `@media (max-width: 900px)` collapse.
- **Show/hide toggle on every password field, site-wide** — a new
  `wirePasswordToggles()` in `shared.js` runs on `DOMContentLoaded`,
  finds every `input[type=password]` on the page, and adds an eye-icon
  button that flips it to `type=text`. No per-page markup change needed;
  applies everywhere `shared.js` is already loaded (login, both signups,
  account password change, profile's API key field, admin's
  practitioner/admin creation forms).
- **Login form**: email now trims on blur (not just at submit) and gets a
  live regex check as the user types — an inline hint appears and submit
  is blocked on an invalid format, instead of only failing after a
  round-trip to the server.
- **Consultation lists show a snippet of the last question.**
  `vault.list_sessions()`/`list_recent_sessions()` now include
  `last_question` (the most recent turn's question, via a correlated
  subquery — no schema change) rendered as a truncated preview on every
  consultation row: Consult's client-overview panel, the dashboard's
  historical-consultations widget, and `client-detail.html`'s
  consultation list all now share the same calendar-icon-plus-snippet
  format.
- The "Phase 2 POC" tag moved out of the sidebar's brand header to its own
  element pinned to the bottom of the sidebar.

## v2.13 — 2026-08-14 (notification badges; dashboard layout widened)

**Dashboards use their available width properly now.** The single-column
stacking from v2.8/v2.9 (a fix for sparse multi-column card grids) went too
far the other way on wide screens, leaving most of the content area empty.
Admin and practitioner dashboards now use a two-column `.layout` (secondary
widgets in a 300px rail, primary content — Pending applications / Historical
consultations — filling the rest); the client dashboard's three stat cards
use a `repeat(auto-fit, minmax(16rem,1fr))` grid instead of a fixed
single column, so they fill the row on wide screens and wrap cleanly on
narrow ones.

**Notification badges** — a small count badge on a sidebar-nav link for
updates the signed-in user hasn't looked at yet, via a new
`setNavBadge()`/`loadAdminNotifications()`/`loadPractitionerNotifications()`
trio in `shared.js`, called from every admin/practitioner page's `load()`:
- **Admin**: badge on Users = count of `pending` practitioner applications
  (`GET /api/admin/notifications`).
- **Practitioner**: badge on Contacts = count of `new`-status contact
  submissions; badge on Dashboard = that count plus unviewed intake
  responses (`GET /api/me/notifications`).
- **Unviewed intake** is new state: `questionnaire_responses.viewed_at`
  (migrated, nullable) is set the moment a practitioner opens a client's
  intake review (`GET /api/me/clients/{id}/intake`, including via Consult's
  overview panel) — `vault.count_unviewed_intake()` counts clients whose
  *latest* response is still unviewed, not just any old unviewed row.
- Explicitly out of scope for now: a per-client-report "unread by the
  client" badge — there's no client-facing view of clinician-authored
  reports yet, so "unread" wouldn't mean anything there.

**Consultation list on `client-detail.html`** now uses the same
calendar-style date marker (large day number, 3-letter month) as the
dashboard's historical-consultations widget, instead of a plain
timestamp — the two lists of the same underlying data now look like the
same thing.

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
