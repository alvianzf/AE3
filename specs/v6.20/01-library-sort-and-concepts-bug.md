# v6.20/01 — Library sort, and a real "0 concepts" bug fix

## Sort by name / date ingested

Direct request: sort the library by file name, date ingested, or date
uploaded, in Icons/List/Table and in Tree view.

Checked the data model before building the "date uploaded" option: a
`Document` only ever persists one timestamp (`ingested_at`, aliased to
`created_at` at the API boundary — same value, two names). The staged
item's own upload-time row (`staged_sources.created_at`) is deleted
the moment promotion into a real `Document` succeeds, so there's no
second, distinct "uploaded at" moment surviving anywhere to sort by —
a document's upload and ingest times are the same fact in this system
(doubly true since `v6.12` removed any real gap between the two events
by auto-ingesting on upload). Built two sort keys, not three: **Name**
and **Date ingested**, each with an ascending/descending toggle.
Persisted to `localStorage`, same convention `viewMode` already uses.

Applies everywhere a document list renders: the Icons/List/Table grid
(`filtered`), and Tree view's per-folder `docs` arrays and root-level
`rootDocs` (previously hardcoded to alphabetical — now use the same
`sortDocs()` helper).

## "Why does the library have 0 concepts?"

A real, pre-existing bug, not something this session's work broke —
found live. The Library tab's own stats line
(`{data.graph.concepts ?? 0} concepts...`) read a field named
`concepts` that `store.graph_stats()` (`app/graph/store.py`) never
actually returns — its real key is `entities`. The `?? 0` fallback
silently masked this since whenever that line was first written; the
stat has always displayed 0 regardless of how many entities the
knowledge graph actually had. Fixed: read `data.graph.entities`
instead.
