# v6.18 — Graph view: visibility, sizing, perf, zoom controls

**Status: implemented.**

- [**01 · Graph view visibility and perf**](01-graph-view-visibility-and-perf.md)
  — four pieces of direct/live feedback in one pass: invisible edges
  (a contrast bug, not a data bug), oversized nodes, no scroll/zoom
  affordance, and real browser-performance cost from unconditional
  stroke-outlined text labels at the concept layer's node count.

## Baseline this builds on

- `v6.13`'s Graph view (`GraphView.svelte`, `documentGraph`,
  `concept_graph()`) — every fix here is a correction to that existing
  component, not new scope.
- `v6.16`'s concept-graph color palette/legend — unaffected by this
  pass's sizing/perf changes.

## What this does not change

No change to the graph's underlying data construction, drag/click
behavior, or SVG-vs-canvas rendering choice — see `01`'s "What this
does not change" for the rest.
