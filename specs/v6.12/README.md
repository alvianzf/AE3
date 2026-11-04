# v6.12 — Auto-ingest queue, no manual staging step

**Status: implemented.**

- [**01 · Remove the staging/review step, auto-queue every upload**](01-auto-ingest-queue.md)
  — the full spec: what already existed (the server-side queue/job
  machinery, built 2026-11-03) vs. what's actually new (auto-ingest on
  upload, cards-in-the-grid instead of a separate tab, a finalize bell,
  a status bar with counts/ETA), plus a real pre-existing bug
  (`'queued'` jobs invisible to a page reload) and a real prod backlog
  this had to account for.

## Baseline this builds on

- `app/ingestion/queue.py`'s concurrency-capped worker pool and the
  `ingestion_jobs` table (same-day batch, 2026-11-03) — this spec adds
  no new durability, it changes when a job starts (immediately, not on
  a manual click) and how its progress is shown (a card in the grid,
  not a separate list).
- The Reader-suggestion / admin-edit-always-wins pattern from `v6.11`
  — the "Placed in library" dialog this reuses for the finalize bell
  already existed.

## What this does not change

No change to the practitioner knowledge page's own (simpler) staged
list, and no change to the `ingestion_jobs`/`staged_sources` data
model — see `01`'s "What this does not change" for the rest.
