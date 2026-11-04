# v6.11 — Document metadata (type, author, uploader) + Library view modes

**Status: implemented.**

- [**01 · Document metadata and view modes**](01-document-metadata-and-views.md)
  — the full spec: what live feedback asked for, what already existed
  vs. was a genuine gap, and the new `Document.doc_type`/`uploaded_by`
  fields plus the three Library view modes (icons/list/table).

## Baseline this builds on

- The Reader-suggestion / admin-edit-always-wins pattern `grade`,
  `folder_path`, and `topics` already established (specs/v6.8/01) —
  `doc_type` follows the exact same shape, just a new field.
- `v6.9/01`'s/`v6.10/01`'s ingest call chain (`_promote_staged_async`
  → `_run_staged_ingest_job` → `_run_ingest` → `store.ingest_document`)
  — `uploaded_by` is threaded through the same chain, not a parallel
  path.

## What this does not change

No change to the practitioner knowledge page's UI, or to the existing
`kind` field (still defaults to `"article"`, still used by script
callers) — see `01`'s "What this does not change" for why both were
left alone.
