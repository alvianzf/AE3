# v6.13 — Knowledge-base graph view

**Status: implemented.**

- [**01 · Graph view**](01-graph-view.md) — the full spec: the two
  switchable layers (documents/folders, concepts), why the concept
  layer is bounded to the top 150 entities by relationship degree
  rather than rendering all 7905+, and why this is hand-rolled on
  d3-force/d3-drag/d3-zoom rather than a wrapper graph library.

## Baseline this builds on

- `v6.8/01`'s folder tree + the Tree view tab's `folderTree`/`rootDocs`
  client-side structures — the document/folder graph layer reuses
  these directly, no new fetch.
- The knowledge graph itself (`Entity`, typed `Entity->Entity`
  relationships) — built at ingest time since the app's original
  GraphRAG design; this is the first UI that actually visualizes it as
  a graph rather than only using it for retrieval.

## What this does not change

No change to the Tree view tab, `GET /api/graph`'s existing
concepts/mentions/unlinked stats, or anything about how the knowledge
graph itself is built — see `01`'s "What this does not change" for the
rest.
