# v6.15/01 — Retry all, Graph view centering, nav active-state bug, doc-card polish

Four pieces of direct/live feedback, shipped together as one batch.

## "Retry all" button

Every staged item in `status='error'` (the real 15-item backlog from
the 2026-11-03 Nebius billing exhaustion is the concrete case this is
for) already had its own per-item Retry button; this adds a bulk one
next to the queue status line, shown only when at least one errored
item exists. No new backend route — there's no dedicated batch-retry
endpoint, so this just calls the existing `ingestOne()` (single-item
`POST /api/staged/{id}/ingest`) once per errored id via
`Promise.all`, same as the existing per-item Retry button does one at
a time.

## Graph view centering

"Graph view is a mess, elements should be centered by default." Root
cause: `forceCenter(width/2, height/2)` only pulls the *center of
mass* toward the middle — it never guaranteed the whole graph (which
can grow wider than the viewport once `forceManyBody`'s repulsion
spreads nodes out, especially the 150-node/~2900-edge concept layer)
actually fit inside the SVG at zoom 1:1. Combined with the zoom
starting at plain identity (no scale/translate chosen to fit
anything), a larger graph simply ran off the visible area.

Fixed with a `fitToView()` that computes the current bounding box of
every node and sets a zoom transform (via `d3-zoom`'s
`.transform()`) that centers and scales it to fit, with padding —
called once after the simulation's initial layout settles. Two things
needed for this not to misbehave:

- **Pre-settle synchronously before first paint.** `d3-force`'s
  default starting positions are randomized, and a strong charge force
  produces a visibly chaotic expansion on every layer switch if left
  to animate from scratch in the browser. `simulation.tick()` called
  manually (not the automatic timer) doesn't dispatch `tick`/`end`
  events per `d3-force`'s own API, so ~300 manual ticks (its own
  default settling time at the default `alphaDecay`) run invisibly
  before anything is rendered, then `fitToView()` runs once against
  the already-settled layout.
- **Only the first settle re-centers.** Dragging a node re-heats the
  simulation (`alphaTarget(0.3)` in `dragNode()`, per the standard
  d3-force drag pattern) which cools back down and fires `'end'`
  again once released — without a `fitted` guard, releasing a dragged
  node would silently reset whatever pan/zoom the admin had set,
  which would have been its own "mess."

Added `d3-transition` as an explicit dependency (previously only
pulled in transitively through `d3-zoom`) since `fitToView()` calls
`.transition()` directly for a smooth recenter instead of a snap-cut.

## Admin nav: Library always showing "active"

"Why is library menu icon always active?" `AppRail.svelte`'s active-
link check was a plain prefix match
(`pathname.startsWith(href + '/')`). The admin rail's Library item has
`href: '/admin'` — the base path every *other* admin route
(`/admin/dashboard`, `/admin/users`, ...) also starts with, so Library
lit up on literally every admin page, not just the library page
itself. Fixed generally (`isActive()`, most-specific-href wins — an
item is active only if no *other* item's href is a longer match for
the current path) rather than special-casing `/admin`, since
`AppRail.svelte` is shared across all three portals; checked the
practitioner/client nav configs and neither currently has a base-path
item like this, but the fix holds for any portal that adds one later.

## Doc-card polish

- **Author vs. uploader, hard to tell apart**: previously one run-on
  line ("By X · Uploaded by Y"), same color/size for both. Now two
  separate lines, each with its own icon (book / user-card) and
  uploader given an accent color — distinguishable by icon, color, and
  layout, not just differently-worded prose.
- **Tags/form fields tightened**: `.tag`/`.tag-input` padding reduced
  (`.15rem .55rem` → `.08rem .45rem`), `.doc-type-select`/
  `.folder-input`/`.grade-label` padding and gaps tightened, and the
  card's own padding reduced (`var(--space-4)` → `var(--space-3)`,
  gap `.5rem` → `.4rem`) for a denser, "neat and tidy" layout per the
  explicit request — font sizes were already at the design system's
  smallest token (`--text-xs`), so density came from padding, not
  inventing a smaller ad-hoc size outside that token scale.
