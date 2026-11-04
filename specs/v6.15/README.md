# v6.15 — Retry all, Graph view centering, nav bug, doc-card polish

**Status: implemented.**

- [**01 · Retry all, Graph view centering, nav active-state bug, doc-card polish**](01-queue-retry-graph-centering-nav-fix.md)
  — four pieces of direct/live feedback: a bulk "Retry all" for
  errored queue items, a real root-cause fix for the Graph view's
  layout not fitting its viewport, a real bug in the shared nav rail
  (Library showing active on every admin page), and doc-card density/
  clarity polish (author vs. uploader, tag/form sizing).

## Baseline this builds on

- `v6.12`'s auto-ingest queue (the errored-item backlog "Retry all"
  retries) and `v6.13`'s Graph view (the layer this fixes centering
  for).
- `AppRail.svelte`, shared by all three portals — the nav fix is
  general, not admin-specific, even though only the admin rail is
  affected today.

## What this does not change

No change to the queue/job data model, the Graph view's two-layer
design, or the nav rail's visual style — see `01` for exactly what
changed in each.
