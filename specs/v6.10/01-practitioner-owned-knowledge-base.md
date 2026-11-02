# v6.10/01 — Practitioner-owned private knowledge base

## What

Any Pro practitioner — not just one an admin has flagged with
`can_upload_library` — can upload a document that becomes part of
their own consults immediately, and only theirs. No admin step, no
review queue, no grading gate beyond the Reader's own automatic
`suggested_grade` every document already gets.

## Why this is a second path, not a mode of the existing one

`can_upload_library` already lets a practitioner contribute to the
**shared** library — admin-curated, graded, visible to every
practitioner subject to the normal grade/weight rules. That path exists
specifically because a shared contribution is a higher-stakes action:
it changes what every other practitioner's consults can surface.

A personal document changes nothing about anyone else's consults —
by construction, it's visible to exactly one practitioner. That's a
fundamentally lower-stakes action, and gating it behind the same
admin-granted permission the shared path needs would block most
practitioners from a feature that can't affect anyone but themselves.
So this is reachable by **any** Pro practitioner
(`auth.require_pro_practitioner` — the same gate consults and the
weighting page already use), independent of `can_upload_library`.

## Reusing v6.9/01, not inventing a second privacy mechanism

A personal document is private by construction, with exactly one
practitioner's standing grant — which is *exactly* what `v6.9/01`
already built: `Document.is_private = true` plus a `document_access`
row. Nothing new is needed in `app/retrieval/seed_search.py`,
`app/graph/store.py`'s `fetch_hop_neighbors()`, or
`app/retrieval/pgvector_store.py`'s `search()` — the same
`accessible_private_ids` check those already gained is, unmodified,
the complete enforcement for this feature too. The only thing missing
is automating the two writes `v6.9/01` expects an admin to make by
hand (`PATCH .../privacy`, `PUT .../access`) at the moment of ingest
instead.

## The missing piece: provenance

Reading `app/main.py`'s `_promote_staged_async`/
`_run_staged_ingest_job`, the `owner` parameter already threaded
through `staged_sources`/`ingestion_jobs` (whose own schema comment
reads "owner: practitioner_id; NULL = admin-initiated") is bookkeeping
for *those* transient tables only — it's never written onto the
resulting `Document`. Today, once ingested, there is no way to tell
which practitioner (if any) a document came from.

**New property: `Document.owner_practitioner_id`**, `null` for every
document ingested through the existing shared-library path (nothing
already in the library changes). `store.ingest_document()` gains this
as an optional parameter; when set, the write also sets
`is_private = true` directly (one write, not a create-then-separately-
privatize round trip), and the caller follows up with
`core_store.set_document_access(document_id, [owner_practitioner_id],
granted_by=owner_practitioner_id)` — a practitioner granting themselves
access to their own upload, same function `v6.9/01`'s admin UI already
calls, just invoked automatically instead of from a dialog.

## The ingest path itself

A new, parallel pair of routes — not a flag on the existing
`can_upload_library`-gated ones, so that permission's meaning doesn't
quietly change:

- `POST /api/me/knowledge/stage` (file or pasted text) —
  `require_pro_practitioner`, otherwise identical to the existing
  `POST /api/staged`.
- `POST /api/me/knowledge/stage/{id}/ingest` — calls the same
  `_promote_staged_async`/`_run_staged_ingest_job`/`_run_ingest` chain
  the admin path already uses (no duplicated pipeline logic), passing
  `owner_practitioner_id=session["id"]` through to
  `store.ingest_document()`, then the self-grant above once the write
  succeeds.

Both routes operate on the practitioner's own staged items only — the
existing `core_store.get_staged_source(staged_id, owner)` ownership
check `_promote_staged_async` already has is reused unchanged, it
simply means something slightly different for a personal item than it
already did for a shared one in progress.

## Where this deliberately diverges from the shared path

- **No folder suggestion.** `v6.8/01`'s folder taxonomy is an
  admin-curated concept for the shared library; a personal document
  always gets `folder_path = ""` and the Reader's `read_source()` call
  for it skips `known_folders` entirely — there's no library-wide
  folder list a one-practitioner document should be nudging an admin's
  taxonomy toward.
- **Admin Library page gets an Owner facet.** Admin still sees every
  document, personal ones included — oversight shouldn't have a blind
  spot just because this path skips admin review going in. But the
  default view should stay the shared library, not be diluted by
  however many practitioners' personal uploads exist — a new facet row
  (`All` / `Shared library` / one entry per practitioner with any
  personal documents) alongside the existing Kind/Folder facets
  (`v6.8/01`), filtering on `owner_practitioner_id`.
- **The owning practitioner can delete their own.** `DELETE
  /api/sources/{id}` stays admin-only (shared-library deletion is a
  curation decision). A new `DELETE /api/me/knowledge/{id}`, gated to
  `owner_practitioner_id == session["id"]` (404 otherwise — don't
  confirm another document's existence), calls the same
  `store.delete_document()` + `pgvector_store.delete_document()` pair
  the admin route already does.
- **An admin can still widen access later.** Nothing stops an admin
  from using `v6.9/01`'s existing `PUT /api/sources/{id}/access` to add
  other practitioners to a personal document's grant list, or
  `PATCH .../privacy` to make it fully public — the same oversight
  capability they have over every other private document. There's no
  dedicated "promote my personal doc to the shared library" action for
  the owning practitioner themselves; if that becomes a real need, it's
  a new, explicit action to design, not something this spec backs into.

## What this does not do

- No cap on how many personal documents one practitioner can hold —
  not a problem this PoC-scale library needs solved yet.
- No sharing directly between practitioners (practitioner A granting
  practitioner B access to A's own document) — only an admin can widen
  a grant, same as `v6.9/01`.
