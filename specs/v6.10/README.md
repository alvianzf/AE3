# v6.10 — Practitioner-owned private knowledge base

**Status: implemented.**

A Pro practitioner can add their own documents to their own knowledge
base — private to them alone from the moment they're ingested, no admin
step required, and counted in only their own consults. Distinct from
both existing mechanisms this builds on:

- [**01 · Practitioner-owned private knowledge base**](01-practitioner-owned-knowledge-base.md)
  — the full spec: why this reuses `v6.9/01`'s privacy/access-grant
  machinery rather than inventing a second one, the new ownership tag
  that machinery was missing, and where it deliberately diverges from
  today's `can_upload_library` path (grading, folders, admin-library
  visibility, delete permissions).

## Baseline this builds on

- `v6.9/01`'s `Document.is_private` + `document_access` table —
  this is the *exact same* enforcement path (seed search, every
  traversal hop, general lookup), just with the grant auto-created to
  the uploading practitioner alone at ingest time instead of an admin
  granting it afterward.
- The existing `can_upload_library` practitioner-upload path
  (`POST /api/staged`, `POST /api/staged/{id}/ingest`) — reused for the
  actual file handling and the Reader/chunk/embed/graph-extraction
  pipeline. What's missing today, confirmed by reading
  `app/main.py`'s `_promote_staged_async`/`_run_staged_ingest_job`: the
  `owner` parameter those already thread through is a bookkeeping field
  on `staged_sources`/`ingestion_jobs` only — it's never written onto
  the resulting `Document` itself, so there's currently no way to know,
  after the fact, which practitioner (if any) a document came from.

## What this does not change

No change to `can_upload_library` or the shared/admin-curated library
path — that remains the only way a document becomes visible to every
practitioner by default. This is a second, separate path a Pro
practitioner can always reach, whether or not they hold that grant.
