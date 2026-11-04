# v6.12/01 — Remove the staging/review step, auto-queue every upload

## What changed

Direct request, verbatim: "Let's remove the staging part... Once user
upload a resource, it will go into root with a flag (not ingested yet),
but it will be queued for ingestion. It will ingested one by one. Queue
will be done SERVER SIDE, so when user refresh, or other admin sees it,
it will show the same thing. Progress bar should be on the document
card. Once it is done, have a notification icon on the card to finalize
the process... Have a status section somewhere that states how many
documents are ingested, and how many are in queue, with expected
estimate time and size."

Before this: uploading/pasting/scraping a source added it to a separate
"Staged for review" tab, where an admin had to click "Ingest" per item
(or select several and batch-ingest) before anything actually entered
the library. After: uploading auto-starts ingestion immediately — no
manual step — and the in-progress item shows as a card in the Library
grid itself (root level, since it has no folder yet) with a progress
bar, not in a separate tab.

## What is, and isn't, new machinery

Nearly everything "server-side queue, survives refresh, visible to
every admin" already needed was already built and already correct:
`staged_sources` (Postgres), `ingestion_jobs` (Postgres, polled by the
frontend), `app/ingestion/queue.py`'s concurrency-capped worker pool
(specs/v6 batch, 2026-11-03), and `GET /api/ingestion-jobs/active` for
reattaching after a reload. This spec's actual surface area:

- **Auto-ingest on stage**: `stageFile`/`stageText`/`scrapeUrl`
  (`web/src/routes/(admin)/admin/+page.svelte`) each now call
  `ingestOne(staged.id)` immediately after staging succeeds, instead of
  leaving the item for a manual click. No backend change needed — the
  stage-then-ingest two-call API already supported this; nothing was
  calling it back to back before.
- **Cards, not a tab**: the "Staged for review" tab is gone. Every
  staged item still in `data.staged` renders as a card
  (`.doc-card-pending`) in the same grid as real library documents
  — root level only, icons/list views only (table view's fixed columns
  don't fit a progress bar well). A finished job's staged row is
  deleted server-side exactly as before (`_run_staged_ingest_job`), so
  the pending card simply disappears and the real document card takes
  its place on the next `invalidateAll()`.
- **Finalize bell, not an auto-popup**: `v6.10`/this session's earlier
  PR had a just-finished ingest auto-open the "Placed in library"
  dialog. With uploads now queuing unattended, popping a dialog over
  whatever the admin is doing is the wrong interruption — replaced with
  a bell icon (`needsFinalization`, a client-side `Set<string>` of doc
  ids, not persisted — a one-time nudge, not queue state) that opens
  the same dialog on click.
- **Status bar**: `GET /api/ingestion-jobs/stats` (new,
  `core_store.ingestion_queue_stats()`) returns queued/processing
  counts, total characters still waiting (from `staged_sources.
  char_count` — no byte-size column exists, chars is the proxy already
  on hand), and a rough ETA from the real duration of the last 10
  completed jobs (`updated_at - created_at`, computed in Python, not
  SQL date math). Refreshed every 5s from the frontend regardless of
  whether this browser is polling any job itself, since the whole point
  is staying correct for another admin's upload too. Shown as one line
  above the library search bar whenever anything is queued.

## A real pre-existing bug this surfaced

`core_store.list_active_ingestion_jobs()` only matched
`status = 'running'` — a job still `'queued'` (waiting for a
concurrency slot, `app/ingestion/queue.py`) was invisible to
`GET /api/ingestion-jobs/active`, so a page refresh while a job sat
queued-but-not-picked-up lost its progress bar entirely until a worker
actually started it. Contradicts the explicit "when user refresh... it
will show the same thing" requirement, and would have been directly
visible under the new design (everything queues up now, concurrency=1
by default per `DEPLOY.md`, so most uploads spend real time in
`'queued'`). Fixed: `WHERE status IN ('running', 'queued')`.

## A real backlog this also had to handle

Checked prod's `staged_sources` table before shipping (not assumed):
17 items from 2026-11-03, 15 with a failed job (`status = 'error'`,
Nebius billing exhaustion at the time) and 2 with no job row at all
(predate this feature — ingestion was never triggered for them).
`list_staged_sources()` now LEFT JOIN LATERALs each item's most recent
`ingestion_jobs` row so the frontend can render the right state on
load without a second round trip per item: an errored one shows its
error (not silently retried), one with no job at all is auto-kicked
off the same way a fresh upload would be.

## What this does not change

- The practitioner knowledge page (`web/src/routes/(practitioner)/
  practitioner/knowledge/+page.svelte`) still has its own separate,
  simpler staged-list UI (a `DataTable`, not cards) — out of scope
  here. It already auto-resumes active jobs the same way; it just
  doesn't get the new card-grid/progress-bar/bell/status-bar treatment
  this spec describes for the admin page.
- `ingestion_jobs`/`staged_sources` themselves are unchanged — this is
  a frontend-flow and one-query change, not a data-model change.
- Duplicate detection is unchanged (`_prep_and_check_duplicate`, still
  a synchronous 409 with replace-or-discard) — now surfaced the moment
  an upload is auto-queued instead of only on a later manual "Ingest"
  click, which is strictly earlier/better feedback, not a behavior
  change.
