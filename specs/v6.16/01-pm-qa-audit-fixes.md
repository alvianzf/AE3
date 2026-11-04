# v6.16/01 — PM + QA audit fixes

Two independent subagent passes over the admin Library feature area
(everything shipped `v6.11`-`v6.15`, 2026-11-04) — one acting as PM
(product gaps), one as QA (code-level bugs), run in parallel with no
visibility into each other's findings. Reconciled here; the highest-
severity/highest-value findings from each were fixed, lower-severity
or larger-scope ones deferred (listed at the end).

## Fixed

### Double-ingest race (QA, highest severity)

Nothing stopped two ingestion jobs from being created for the same
staged item — a double-click on Retry, or the page-load auto-kick-for-
job-less-items loop racing a manual click. The frontend's `watchJob`
polling is keyed by `stagedId`, so starting a second job silently
stopped tracking of the first; if the first then won the Neo4j write
(a `content_hash` uniqueness race), its completion was never observed
— the second job's `ConstraintError`-derived 409 reported the whole
operation as "failed" even though the document had, in fact, been
ingested. The stale staged-item card lingered (no `invalidateAll`
fired by the untracked winner), and Discard on it would 404 (the
staged row was already deleted by the winning job).

Fixed at the root: `core_store.get_active_job_for_staged()` (new) +
a check in `_promote_staged_async()` — a request for a staged item
that already has an active (`queued`/`running`) job reattaches to that
job's id instead of creating a second one. Not fully race-proof (no
DB-level unique constraint backs this — a true simultaneous-request
TOCTOU window remains), but closes the actual reachable case: a
double-click is two sequential requests, not two that execute the
check in the same instant.

Also fixed `retryAll()` (`v6.15`) to run sequentially, not via
`Promise.all` — concurrent retries could each independently hit a
duplicate-409 and clobber each other's single shared dialog state
(`duplicateStagedId`/`duplicateOf`/etc. are page-level variables, not
per-item). The batch now stops the moment one duplicate dialog opens
rather than racing into the next item's.

### Graph view's own "centered by default" fix (`v6.15`) was itself buggy

`fitted` (the guard meant to let only the *first* settle re-center the
view, not a later one from a node drag re-heating the simulation) was
set `true` unconditionally right after the synchronous pre-tick warm-
up loop, regardless of whether that loop actually converged within its
300-tick budget. For a graph that genuinely needs more ticks — the
~150-node/~2900-edge concept layer is exactly the case the original
"a mess" bug report was about — the real `on('end', ...)` handler was
now permanently skipped, so the view was fit once against still-
unsettled positions and never re-fit once the simulation kept moving.
Reproduced the exact bug the surrounding comment claimed was fixed.
Fixed: the pre-tick loop's `fitToView()` call is now a best-effort
first paint that does *not* mark `fitted` — the guarded handler still
fires the real fit the first time the simulation actually ends,
whether that's on the very next frame or later.

### Blank, feedback-less search dead end

Browsing a folder that has subfolders, then searching for something
that matches zero documents, used to render nothing at all — not even
a "nothing matches" message — because the empty-state paragraph was
gated on `!visibleSubfolders.length`, independent of whether a search
was active (subfolder tiles themselves were already correctly hidden
while searching). Fixed: the empty-state message now also shows
whenever `searching` is true, regardless of subfolder count.

### Folder move/rename to root corrupted the current browse path

Moving or renaming a folder you're browsing a descendant of, to the
*root* specifically (`newPath = ''`), produced a `currentPath` like
`"/B/C"` — a leading slash no real `folder_path` ever has — because
the old code concatenated `newPath + currentPath.slice(oldPath.
length)`, and that slice already includes the separator slash. Once
non-empty, nothing in the library matched the corrupted path (it fell
through every `folder_path` comparison), silently showing an empty
folder with a broken-looking breadcrumb until the admin navigated
elsewhere by hand. Fixed: the suffix now drops both `oldPath` and its
following slash before re-prefixing.

### `saveAccess()` was the one mutating action that never refreshed data

Every sibling write on this page (`setTopics`, `regrade`, `setFolder`,
`setDocType`, `setPrivate`, `confirmAssignUploader`, ...) calls
`invalidateAll()` after a successful save; `saveAccess()` didn't. Added.

### Audit log recorded edits against documents that don't exist

`set_doc_type()`/`set_uploaded_by()` (`v6.11`/`v6.14`) called `log()`
unconditionally, even when the `MATCH`/`SET` matched nothing (a
nonexistent `document_id` — the route correctly 404s on this, but the
audit trail still recorded "set doc_type → X" for an edit that
provably did nothing). Fixed: both now log only when `get_document()`
confirms the write actually landed.

### Dead "Kind" filter chips removed

`kind` (the upload-method field, confirmed in `v6.11` to always be the
literal string `"article"` in practice) still had its own filter-chip
row directly above the documents grid, right next to the real,
Reader-driven `doc_type` dropdown `v6.11` introduced specifically
because `kind` wasn't useful for this. Two type-looking controls that
meant different things, one of them already known to carry zero
information. Removed the dead filter row and `activeKind` state
entirely (`data.kinds` itself is left alone — harmless unused data,
not worth chasing further plumbing removal for this pass).

### Graph view tab had no graph stats on itself

The "N concepts · N links · N unlinked sources" line only rendered on
the Library tab. An admin who clicked straight into Graph view to
judge the graph's health had no counts anywhere on that tab. Added the
same line there.

### Concept graph: every node the same color, no legend

`GraphView`'s color map only defined `folder`/`document` (the
document-graph layer's two groups); concept-layer nodes are grouped by
entity type (`Symptom`, `Treatment`, `hormone`, ...) — an open,
unbounded set from the KG-builder, not those two keys — so every
single concept node fell through to the same `var(--muted)` gray. The
one feature meant to show a *typed* knowledge graph was visually
undifferentiated by type, distinguishable only by circle size. Fixed:
a fixed 10-color palette assigned to each distinct group found in the
current node set, in sorted (stable, not hashed/flickering) order,
with a small color-swatch legend rendered below the graph whenever any
palette colors are in use.

## Deferred (real findings, not fixed this pass)

Noted for a future pass — either lower severity, a genuine design
tradeoff already made deliberately in an earlier spec, or a larger
scope than this reconciliation pass:

- **Table view's action parity** (PM): View/Move/Delete only — no
  private/public toggle, Edit access, or Assign uploader, and no
  visibility into staged/in-progress items at all. The biggest
  standing product gap; fixing it properly means deciding how those
  actions fit a table row (another "⋮" menu per row? inline icons?)
  rather than a quick patch.
- **Search doesn't work in Tree/Graph view tabs** (PM) — the search box
  only renders on the Library tab.
- **Bulk actions limited to private/public** (PM) — no bulk move,
  delete, tag, or doc-type.
- **Duplicate-detection dialog has no link to preview the colliding
  document** (PM) — the admin picks replace-or-discard blind.
- **No visual indicator a folder (or its contents) is private** (PM) —
  neither the folder tree nor folder-card tiles show a lock badge.
- **`needsFinalization` bell is lost on refresh** (PM) — intentional
  per `v6.12`'s own "per-browser, not persisted" design; flagged again
  here since auto-ingest now runs fully unattended, making this the
  only mechanism ensuring a human eventually reviews a placement.
- **Practitioner-owned documents' `uploaded_by` is captured but never
  shown anywhere** (PM).
- **Terminology sprawl** across one ingest flow ("staged" → "queued" →
  "Ingesting…" → finalize bell → "Placed in library") (PM).
- **ETA formula ignores `INGESTION_CONCURRENCY` &gt; 1** (QA) — latent,
  masked by the current default of `1`.
- **One-poll-cycle progress-bar flicker on reload** for an active job
  (QA) — cosmetic only.
- **Orphaned `ingestion_jobs` rows** after a losing duplicate race
  (QA) — data hygiene, not user-visible, and the job-dedup fix above
  makes the specific race that caused it far less reachable.
- **`placementPreview` dialog doesn't self-close if its document is
  deleted out from under it** (QA) — narrow edge case.
- **`promotingId`'s single shared value** across a (now-sequential)
  `retryAll()` batch (QA) — the sequential fix above already removes
  the actual race window; a dedicated per-item busy-state would be
  pure polish on top.
