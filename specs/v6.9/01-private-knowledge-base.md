# v6.9/01 — Private knowledge base

## What

An admin can mark a document, or a whole folder at once, as private.
A private document disappears from every practitioner's consult results
— seed search and graph traversal both — except the specific
practitioners the admin has explicitly granted access to. Granting or
revoking takes effect immediately, the same "checked at request time,
not cached" posture `can_upload_library` already has.

## Data model

**`Document.is_private: bool`**, default `false` — a plain property,
same pattern `folder_path` already uses, not a new node type. Every
existing document defaults to `false` on deploy; nothing already in the
library changes visibility.

**A new core-store table, not a per-practitioner vault table:**

```sql
CREATE TABLE document_access (
    document_id TEXT NOT NULL,
    practitioner_id TEXT NOT NULL REFERENCES practitioners(id),
    granted_at TEXT NOT NULL,
    granted_by TEXT NOT NULL,       -- admin id, for the audit trail
    PRIMARY KEY (document_id, practitioner_id)
);
```

Lives in `app/core_store.py`'s `public` schema (`ensure_schema()`), next
to `admins`/`practitioners`, **not** inside each practitioner's own
`vault_<id>` schema the way `app/vault.py`'s `source_weights` does.
Reasoning: `source_weights` is a practitioner's own opinion about a
document they can already see (how much to trust it); an access grant
is the admin deciding who gets to see the document at all — an admin
action, same category as the existing `can_upload_library` flag
(`core_store.py`'s own comment: "An explicit per-practitioner grant, not
a blanket perk — a superadmin/admin decides WHICH practitioners get
it"). A document lives in Neo4j, not Postgres, so this is necessarily a
cross-store reference by plain id — no foreign key to the Document
node, same as `vault.py`'s `source_weights.source_id` already is.

`document_id` has no FK target on the Neo4j side (can't, different
database) — a stale row (document deleted, access grant left behind) is
harmless dead data, same category of harmlessness
`originals.delete()`'s docstring already accepts for an orphaned
original file; not cleaned up automatically, cheap to ignore.

## Where enforcement actually has to live

A private document can reach a consult's answer through three separate
paths, and all three need the same check — missing one would make
"private" a leak, not a real boundary:

1. **Seed search** (`app/retrieval/seed_search.py`'s `seed()`) — the
   vector/full-text hits it gets back from `store.seed_chunks_by_vector`/
   `_fulltext` already carry `document_id`. The existing weight-aware
   grade filter (`weights.get(r.get("document_id"), r.get("grade", 0))
   >= min_grade`) gains a sibling check: a hit whose document is private
   is dropped unless the requesting practitioner has a `document_access`
   row for it.
2. **Graph traversal, every hop** (`app/graph/store.py`'s
   `fetch_hop_neighbors()`) — this is the exact function whose docstring
   already explains why the grade check has to be enforced "at every
   later hop," not just at the seed: a private Chunk could otherwise be
   pulled in two hops deep, past the point anything checked it. Needs
   the same accessible-document-id set threaded through
   `GraphTraversalRetriever` the way `weights` already is end to end
   (`app/main.py` → `seed_search.seed()` → `traversal.py`'s
   `GraphTraversalRetriever.__init__`).
3. **General lookup** (`app/retrieval/general_lookup.py`) — the
   pgvector-backed "fast path" `retrieval_mode: "general_lookup"`
   bypasses Neo4j and `fetch_hop_neighbors` entirely, so it needs its
   own copy of the same check against `pgvector_store`'s mirrored
   `document_id` column, or it becomes the one path that ignores privacy
   outright.

A practitioner's own `GET /api/me/knowledge` listing (the weighting
page, `v6.7/03`'s viewer) also needs the same filter — a private
document that practitioner has no grant for should not appear there
either, not just be excluded from consult results while still visible
and viewable in the library browser.

## Admin UI

### Bulk-select, over the already-ingested library (not the staged queue)

The admin Library page already has one multi-select mechanism
(`selected`, a `Set<string>` in `+page.svelte`) — but it's scoped to the
staged-upload review queue ("Ingest selected," the commit this spec's
request echoes almost exactly). This is a second, independent selection
set over the doc-grid cards themselves (a checkbox per card; a bulk
action bar appears once at least one is checked) — a different list
with a different lifecycle, not a reuse of the staged-queue one.

- **Per-document**: a "Make private"/"Make public" toggle in the
  existing per-card action row, alongside the grade input and the new
  folder field (`v6.8/01`).
- **Bulk, over a multi-selected set of cards**: the same action, applied
  to every selected document in one request.
- **Bulk, over a whole folder**: triggered from the folder tile itself
  (`v6.8/01`'s folder facet row) — "Make everything in this folder
  private." Implemented as the exact same prefix-match bulk write
  `rename_folder()` already does (`WHERE doc.folder_path = $path OR
  doc.folder_path STARTS WITH $path + '/'`), just setting `is_private`
  instead of rewriting `folder_path`.

### The folder-privacy tradeoff, stated plainly

"Privatize this folder" is a one-time bulk action over whatever's in
the folder *right now* — not a persisted folder-level policy. A document
ingested into that same folder path tomorrow is public by default, same
as any new document, and needs its own explicit privacy action. This is
the same known limitation `v6.8/01` already names for its string-prefix
folder model ("no persistent per-folder policy without a first-class
Folder entity") — not solved differently here. If a standing "everything
placed under `Internal/` is private by default" rule becomes a real
requirement, that's the same future `:Folder` node `v6.8/01` already
flags as the point to revisit, not something this spec works around
with a second mechanism.

### Granting access

Privatizing (single, bulk, or folder) immediately opens a practitioner
multi-select (the existing practitioner list, same data
`web/src/routes/(admin)/admin/users/+page.svelte` already loads) to
choose who can still see it. Reachable again later from a private
document's own row — an "Access" action opening the same multi-select,
pre-checked with its current grants — so the grant list isn't frozen at
the moment of privatization. Saving replaces the full grant list for
that document in one call (same simplicity `can_upload_library`'s
single-flag-flip already has — not an incremental add/remove diff).

## What this does not do

- No persisted per-folder privacy policy — see the tradeoff above.
- No groups/roles for granting — one admin action, one multi-select of
  individual practitioners, every time.
- Nothing client-facing — the client portal has no library browsing
  today, and this doesn't add any.
