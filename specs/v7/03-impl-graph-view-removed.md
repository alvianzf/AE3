# v7/03 (addendum) — Graph view removed from the admin Library, for now

**Status: implemented.** Direct instruction: "Remove the graph view
for now."

## What changed

The "Graph view" tab (`specs/v6.13`, `v6.18`'s fixes on top of it) is
removed from the admin Library page's tab list — the tab entry, the
layer-toggle markup, the `documentGraph`/`conceptGraph` state and
`loadConceptGraph`/`onGraphNodeClick` logic, and the now-dead
`.graph-layer-toggle` CSS.

**Reversible, not deleted outright** — per "for now": `GraphView.svelte`
itself, the backend `GET /api/graph/concepts` route, and
`store.concept_graph()` are untouched. Re-adding the tab is wiring
work only (re-add the tab entry, the toggle markup, and the two state/
derived blocks this removed), not rebuilding anything from scratch.

## Verification

`npm run check` — 0 errors, no new warnings beyond the existing
baseline.

## What this does not change

No change to the Tree view tab, Icons/List/Table views, or any other
part of the Library page — this removal is scoped to the Graph view
tab alone.
