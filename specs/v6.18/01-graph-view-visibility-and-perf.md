# v6.18/01 — Graph view: invisible edges, node sizing, perf, zoom controls

Four pieces of direct/live feedback on `v6.13`'s Graph view, in one
pass.

## "Graph view does not have any connecting dots/lines"

Not a data bug — `documentGraph`/`concept_graph()` always push an edge
for every non-root node (confirmed by re-reading both). The edges were
there; they didn't render *visibly*. `GraphView.svelte`'s `.edge`
stroke was `var(--line-2)` (`#d9d4cc`, a pale tan-gray) at 1px on a
white (`var(--panel)`) background — essentially invisible, especially
under node circles and stroke-outlined text. Fixed: `stroke:
var(--muted)` (a real contrast color already used elsewhere for
secondary UI text) at `1.2px`/`opacity: .5`.

## Dots too big

Node `size` values halved roughly across the board: document-graph
folders 7/8 → 5/6, documents 4 → 3; concept-graph sizing formula
`5 + min(14, sqrt(mentions)*2)` → `3 + min(7, sqrt(mentions))` (smaller
base, smaller growth range, smaller cap).

## Needs to be scrollable and interactive

- `.graph-wrap` gained `overflow: auto` and a `max-height: 70vh` (was
  unbounded height, `overflow: hidden`) — the SVG is sized to exactly
  fill its container via the existing `ResizeObserver`, so this is a
  literal scroll container, not purely decorative; it also caps how
  tall the Graph tab can grow on a large viewport.
- Explicit zoom controls (+ / − / reset) added as an overlay — wheel-
  zoom and drag-to-pan already worked (native `d3-zoom` defaults on
  the whole `<svg>`), but nothing visibly signaled the graph was a
  navigable thing rather than a static diagram. `zoomBy()` wraps the
  existing `zoomBehavior.scaleBy`; reset calls the existing
  `fitToView()`.
- `svg { touch-action: none }` added so touch-drag/pinch (d3-zoom's
  touch support) doesn't fight the browser's own scroll/zoom gestures
  on mobile.

## Graph is really heavy on the browser

Root cause: every node's `<text>` label is stroke-outlined (`paint-
order: stroke; stroke-width: 3px`) for legibility against overlapping
edges — relatively expensive to rasterize — and was rendered
unconditionally for every node, every frame, regardless of whether it
was even legible at the current zoom level. At the concept layer's
scale (~150 nodes before this pass) that's a lot of expensive text
painting for labels nobody could read while zoomed out anyway.

Two changes:
- `store.concept_graph()`'s default `limit` lowered 150 → 80 — directly
  cuts both node count and (since edges scale with the node set)
  rendered edge count for the single heaviest layer.
- `GraphView.svelte` now tracks the live zoom scale (`zoomScale`,
  updated from the existing `d3-zoom` `'zoom'` handler) and a
  `hoveredId`. For graphs at or under 60 nodes (true for every
  document/folder-layer graph in practice, and now most concept-layer
  loads too) every label still renders unconditionally — no visible
  behavior change for the common case. Past that threshold, a node's
  label only renders when zoomed in past `1.4x`'s useful range
  (`zoomScale > 0.8`) or while that specific node is hovered — cutting
  the dominant render cost exactly in the regime (zoomed-out, dense)
  where the labels were both expensive and unreadable anyway.

## What this does not change

- No change to `documentGraph`'s or `concept_graph()`'s actual node/
  edge *construction* logic beyond the one `limit` default and the
  `size` formula — the underlying graph data was always correct.
- No change to the drag-to-reposition or click-to-navigate behavior.
- Did not switch rendering to `<canvas>` — SVG stays the renderer;
  cutting label count was enough of a win at this data scale (≤80
  concept nodes, a folder tree) to not justify that larger rewrite.
