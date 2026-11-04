# v6.13/01 — Knowledge-base graph view

## What

A new "Graph view" tab on the admin Library page, with two switchable
layers, per the user's explicit choice when asked which layer(s) the
graph should show ("Both, as switchable layers"):

- **Documents & folders** — the same tree the Tree view tab already
  renders (`v6.8/01` addendum), as a force-directed node-link diagram
  instead of a nested list. Built entirely client-side from
  `folderTree`/`rootDocs` (already computed for the Tree view tab) —
  no new fetch, no new backend query.
- **Concepts** — the actual knowledge graph this app builds at ingest
  time: typed `Entity->Entity` relationships (`TREATS`, `CAUSES`, ...),
  not the citation/retrieval graph. A real network call
  (`GET /api/graph/concepts`, new), fetched once on first pick and
  cached client-side for the rest of the session.

## Why a bounded concept graph, not the whole thing

Production has 7905+ `Entity` nodes. Rendering all of them is neither
useful (an unreadable hairball) nor performant in a browser's SVG/force
simulation. `store.concept_graph(limit=150)` takes the top `limit`
entities by **typed-relationship degree** — how connected a concept is
to *other concepts* — not raw `MENTIONS` count, which just reflects how
often a chunk happens to say a given term and says nothing about how
central it actually is to the graph's structure. Mention count is still
returned per node (used for circle sizing/tooltip), just not the
primary ranking.

## Why hand-rolled d3, not a wrapper graph library

Added `d3-force`, `d3-drag`, `d3-zoom`, `d3-selection` (plus their
`@types/*` for the type-checker) — the physics/interaction primitives
only. Considered `force-graph` (a popular single-package wrapper) first
and checked its actual dependency tree before deciding against it: it
pulls in a canvas renderer and styling opinions of its own, plus
`lodash-es`, `@tweenjs/tween.js`, `bezier-js`, `canvas-color-tracker`,
`float-tooltip` — a much larger, less inspectable dependency surface
for a feature used at exactly one place in the app. The four d3
modules used here are each single-purpose with minimal transitive
dependencies (`d3-timer`, `d3-dispatch`, `d3-quadtree`,
`d3-transition`, `d3-interpolate` — no unrelated code pulled in), and
rendering to plain SVG (not canvas) means the graph's styling comes
from this app's own CSS variables (dark mode included) rather than a
library's own theming layer.

`web/src/lib/components/GraphView.svelte` is the generic piece: takes
`nodes`/`edges` props (`{id, label, group?, size?}` /
`{source, target, label?}`), runs the simulation in an `$effect`,
renders `<circle>`/`<text>` per node and `<line>` per edge directly
from `$state`-proxied simulation objects (d3-force mutates `x`/`y` on
each node in place every tick; since the backing array is `$state`,
that in-place mutation is reactive on its own — no manual "something
changed" counter needed), with `d3-drag` for dragging a node (sets
`fx`/`fy` to pin it, same as any standard d3-force example) and
`d3-zoom` on the root `<g>` transform for pan/zoom.

## Backend

`store.concept_graph()` (`app/graph/store.py`) — two plain Cypher
queries in one session (not one combined query): the top-N entities by
degree, then every typed edge where both ends are in that set. Kept as
two simple queries rather than one more clever one, matching this
file's existing style (`coverage()`, `graph_stats()` — small, readable
queries over one big one). `GET /api/graph/concepts`
(`app/main.py`, admin-only) exposes it.

## What this does not change

- No change to the Tree view tab — it stays a nested list; the
  document/folder *graph* layer is a different visualization of the
  identical underlying data, not a replacement.
- No change to `graph_stats()`/`GET /api/graph` (concepts/mentions/
  unlinked counts on the dashboard) — this is a new, separate query.
- Clicking a document node opens its detail page in a new tab;
  clicking a folder node jumps to the Library tab at that path — same
  navigation behavior the Tree view tab already has. Concept nodes
  aren't currently clickable to anything (no obvious single
  destination — a concept relates to many documents) — left inert
  rather than guessing at one.
