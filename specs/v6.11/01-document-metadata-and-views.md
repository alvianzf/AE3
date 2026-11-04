# v6.11/01 — Document metadata (type, author, uploader) + view modes

## What prompted this

Live feedback, 2026-11-04: "would it be possible to change the view on
documents (icons/list/columns), see the author, see who uploaded the
document, and choose which tags/which content type (article, book,
presentation, protocol, picture, etc.) a document is?"

Checked against the code before building anything:

- **Tags** already worked (the `+tag` chip input on every doc-card).
- **Author** was already extracted by the Reader and stored on
  `Document.author`, but nothing in the UI displayed it.
- **Uploader** was not tracked end to end. `staged_sources.created_by`
  records who staged an item, but that row is deleted once promotion
  succeeds and nothing carried the identity onto the resulting
  `Document` — there was no way to answer "who uploaded this" after
  the fact.
- **Content type** (article/book/presentation/...) did not exist as a
  field anywhere. The `kind` chip already visible on every card looked
  like it might be this, but it isn't: `kind` is a free-text field that
  defaults to `"article"` at upload time (`add_source`'s
  `Form("article")` default, `StagedIngestBody.kind`'s same default)
  and nothing in the admin UI ever sets it to anything else — so in
  practice every document's `kind` is the literal string `"article"`.
  It's dead weight, not a working classifier.
- **View modes**: only ever a card grid.

## What this adds

### `Document.doc_type` — a real, Reader-suggested classification

A new document property, separate from `kind` (left alone — still used
internally and by script callers like `verify.py`, just never
meaningfully populated). `doc_type` is constrained to a fixed list
(`store.DOC_TYPES`): `article, book, presentation, education material,
lecture notes, protocol, picture, chart, other`.

- `app/ingestion/pipeline.py`'s `READER_SCHEMA` gained a `doc_type`
  field (`enum: store.DOC_TYPES`) — the Reader classifies it at ingest
  time, same as `suggested_grade`/`suggested_folder`.
- `store.set_doc_type()` / `PATCH /api/sources/{id}/doc-type` — an
  admin's edit always wins over the Reader's suggestion, the same
  "suggestion is just the starting value" relationship grade, folder,
  and topics already have. `GET /api/doc-types` exposes the fixed list
  so the frontend doesn't hardcode it against a second copy (the admin
  page does still keep its own literal copy for now — small enough,
  and a GET round-trip wasn't worth it for 9 fixed strings. Revisit if
  this list grows or needs to change without a redeploy).

### `Document.uploaded_by`

Set once, at ingest time, from the acting admin's email or
practitioner's name (`app/main.py`'s new `_caller_identity()` helper —
one extra DB lookup, since the session cookie itself only carries
role/id, not email/name). Threaded through every path that reaches
`store.ingest_document()`: the synchronous `add_source` /
`source_upload_complete` routes, and the staged-promotion path
(`promote_staged`, `promote_staged_batch`, `promote_own_staged` →
`_promote_staged_async` → `_run_staged_ingest_job` → `_run_ingest`).

Not backfilled — existing documents show `uploaded_by: ""` (rendered
as nothing in the UI) rather than a guessed value.

### Frontend (admin Library page)

- Author + uploader shown as a small meta line under each doc-card's
  tag row, only when either is non-empty.
- `doc_type` shown as an editable `<select>` in the doc-card footer,
  replacing the old always-"article" `kind` chip (zero information
  value — every card showed the same word). Same select also added to
  the "Placed in library" post-ingest dialog (v6.10's follow-up),
  alongside the folder/tag editors already there.
- Three view modes — icons (the original card grid, default), list
  (same cards, one per row — just a CSS `grid-template-columns: 1fr`
  switch, no markup duplication), and a table/"columns" view (a
  genuinely different compact render: title, type, author, uploaded
  by, folder, tags, grade, date, and a few icon actions per row — tags
  are read-only here, edit them from Icons/List). Persisted to
  `localStorage` per browser, not server state.
- Search is already library-wide once you type something
  (`searching`'s flat-filter branch, specs/v6.8/01) — extended to
  match against `folder_path`, `doc_type` was considered but left out
  of the free-text match (it's a short fixed-vocabulary dropdown, not
  prose worth full-text matching), and `topics` in addition to the
  existing title/summary/origin/author/filename fields, so a search
  for a tag or folder name now surfaces its documents too.

## What this does not change

- No change to the practitioner knowledge page's UI — it has no
  tag-editing affordance to put a `doc_type` selector next to yet, and
  wasn't in scope here. `uploaded_by` is still captured for
  practitioner-owned documents (via `_caller_identity(session)` in
  `promote_own_staged`), just not surfaced there.
- `kind` is untouched — still defaults to `"article"`, still exists for
  the script callers that pass it explicitly. Not removed: several
  routes still thread it through, and ripping it out was a bigger,
  unrelated change than this spec needed.
