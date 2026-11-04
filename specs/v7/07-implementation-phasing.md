# v7/07 — Implementation phasing

No single PR implements this redesign — every other spec in this repo
ships as independently reviewable, independently deployable work, and
this is no exception, especially at this scope (4 surfaces, ~20
distinct pages, 2 new shared primitives). Phases below are ordered by
a mix of risk (foundation before the pages that depend on it),
visibility (the landing page is the first thing a new visitor sees),
and value (Library is the admin portal's highest-traffic page).

Each phase is its own branch → PR → CI → (explicit user "merge")
→ deploy → live health check, same workflow every prior spec in this
session has already followed. No phase starts implementation before
its own corresponding spec section above has been reviewed — this
document itself does not authorize building anything; it's the
sequencing plan for once that review happens.

## Phase 0 — Design system foundation (`01`)

Token additions to `app.css` (type scale, named weights/durations/
easing, container/breakpoint documentation) plus the two genuinely new
shared components with no page depending on them yet:
`EmptyState.svelte`, `Skeleton.svelte`. Landed first and alone,
because every later phase either consumes these tokens directly or
is meaningfully cheaper to build once they exist. Lowest risk of this
whole plan — additive tokens, two new standalone components, zero
changes to any existing page's rendered output.

**Verification**: `npm run check` (0 errors, same bar every PR this
session has held), a visual diff of every existing page confirming
*zero* visible change (token additions only, nothing consumed yet).

## Phase 1 — Landing page + public nav (`02`, partial)

The landing page redesign (icon pillars, scroll-triggered reveals,
the product-glimpse decision) plus `PublicNav.svelte`'s visual
refresh. Highest-visibility, lowest-complexity page to redesign
first — no auth, no portal-specific data, a contained blast radius.
`/practitioners`/`/join`/`/login`/`/signup` follow as their own
sub-phases once each gets its own detailed read (per `02`'s own
stated gap).

**Verification**: Lighthouse/visual QA on the live deploy (the public
site is the one surface with zero auth friction to manually re-check
after every change), confirm `Seo.svelte`/JSON-LD/`sitemap.xml`
outputs are byte-identical (no SEO/GEO regression from a purely
visual change).

## Phase 2 — Admin Library page (`03`, Library section)

The highest-value single-page phase: `Card.svelte` consolidation
(replacing `.doc-card`/`.folder-card`/`.staged-row`'s independently-
maintained CSS), `EmptyState.svelte` adoption. Command palette and
onboarding tour for this portal land in their own later phase (6/7
below) once the generic `CommandPalette.svelte`/`Tour.svelte`
components exist — building them against this page first, then
porting to the other two portals, is cheaper than building the
generic version blind.

**Verification**: given this page's history of exactly the kind of
subtle regression a visual refactor risks (`v6.16`'s PM+QA audit found
several real bugs in this same page), a dedicated QA pass (the same
two-subagent PM+QA pattern already used once this session) before
merge, not just `npm run check`.

## Phase 3 — Remaining admin portal pages (`03`, Dashboard/Users/
Questionnaires/Audit)

Each gets its own read-then-spec-then-implement cycle, landed as
separate PRs — these pages are lower-traffic and lower-risk than
Library, so batching 2-3 per PR is reasonable once their specs exist,
unlike Library's dedicated solo phase.

## Phase 4 — Practitioner portal (`04`)

Consult first (highest-value, per `04`'s own framing), then Clients/
Knowledge, then the rest. `Card.svelte`/`EmptyState.svelte` from
Phase 0 are already available by this point — this phase is mostly
page-specific polish + `01`'s tokens, not new shared-component work.

## Phase 5 — Client portal (`05`)

Same shape as Phase 4, scaled to this portal's smaller surface area
(5 pages). Includes a fresh "act as a first-time client" audit pass
before implementation, per `05`'s explicit call-back to the `v6.6`
audit method.

## Phase 6 — Command palette (`06`)

Built once, against the admin portal first (richest action set to
validate the generic component against), then wired into practitioner
and client portals' `+layout.svelte` files with their own entry
lists. A cross-cutting phase deliberately sequenced *after* the
per-portal content phases above, not before — the palette's entry
list for each portal is most naturally derived from having just
rebuilt that portal's own pages, not guessed at in advance.

## Phase 7 — Onboarding tours (`06`)

Last, for the same reason as Phase 6: each portal's tour content
references real, already-redesigned UI elements (so a tour step's
callout target still exists and looks like the tour describes it) and
depends on the new server-side "has completed tour" flag, which this
phase adds.

## Cross-phase practices

- Every phase gets its own `specs/v7/0N-*` implementation note once
  built (mirroring every other version in this repo — "implemented"
  status, what changed, what was found live if anything), not just
  this planning document.
- No phase merges without the user's explicit "merge"/"deploy"
  confirmation, per this session's established workflow — the standing
  3-hour merge/deploy permission already granted covers the hotfixes
  shipped in parallel with this spec, not a blanket pre-approval for
  an undetermined number of future redesign PRs; each phase still gets
  its own explicit go-ahead when it's actually ready, unless the user
  says otherwise.
- A phase that touches a page with real users actively depending on
  it in production (Library, Consult) gets a live smoke test
  immediately after deploy, same as every hotfix this session has
  already done — not just CI green.
