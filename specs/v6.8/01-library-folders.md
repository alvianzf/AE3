# v6.8/01 — Library folders

## What

Every source in the knowledge library gets a folder path — e.g.
`Hormones/Menopause`, or `""` for the root. Admins (and superadmins; the
same `auth.require_admin` gate the Library page already sits behind)
organize sources into folders and subfolders. The Reader suggests a
path and a folder name at ingest time; the admin's decision is what
actually gets stored, and can be changed at any time after.

## Why a suggestion, not an automatic placement

The existing `source_card_summary`/topics/grade flow already makes this
exact tradeoff: the Reader proposes, the admin can see and override
every field before (or after) it lands. Folder placement is the same
shape of decision — it benefits from the Reader having just read the
document (it knows what's actually in it, an admin skimming a title
might not), but it's a judgment call about *this library's* taxonomy,
which the Reader has no authority over. Auto-filing would also mean an
admin discovers their folder structure by accident, one ingest at a
time, instead of deciding it.

## Data model

A single `folder_path` string property on `:Document`, same pattern
`topics`/`grade`/`origin` already use — not a separate `:Folder` node
type. Reasoning:

- A folder with zero documents in it isn't a real requirement here (the
  request is "organize uploaded knowledge base," not "let admins build
  out an empty taxonomy ahead of time") — the library's folder tree is
  always just the distinct set of `folder_path` values currently in use,
  the same way `store.facets()["topics"]` already derives the topic
  list from whatever's actually tagged, not from a separate topics
  table.
- Renaming a folder is renaming a string prefix shared by every document
  under it — `UPDATE Document SET folder_path = replace(folder_path,
  $old, $new) WHERE folder_path STARTS WITH $old`, one Cypher statement,
  not a cascade across a separate node hierarchy.
- `""` (root) is the default for every source ingested before this
  ships — no backfill migration needed, nothing in the existing library
  changes location on deploy.

`/` is the path separator; a leading/trailing `/` is stripped on write
so `"Hormones/Menopause"`, `"Hormones/Menopause/"`, and
`"/Hormones/Menopause"` all normalize to the same folder. A segment
name is admin-entered free text (same validation posture as a source's
`title` today — no new character restrictions), so renaming is literal
text substitution, not an id lookup.

If this library later needs folders with no documents yet (a real future
requirement, not assumed here), that's the point to add a first-class
`:Folder` node — flagged here as the known limitation of the
string-prefix design, not solved preemptively.

## Reader suggestion

`app/ingestion/pipeline.py`'s `READER_SCHEMA` gains two optional fields,
alongside the existing `topics`:

```python
"suggested_folder": {
    "type": "string",
    "description": "A suggested folder path (e.g. 'Hormones/Menopause'), "
                   "taken from the library's existing folder list "
                   "wherever one fits. Empty string if none fits well.",
},
```

`read_source()` already takes `known_topics` (today:
`store.facets()["topics"]`) specifically so the Reader files a new
source beside its neighbours instead of coining a new label every time;
`known_folders` (a new `store.facets()["folders"]` — the distinct,
non-empty `folder_path` values in use) is the exact same mechanism,
passed the same way. This is additive to the existing structured call —
no new Reader invocation, no new AI-team role.

The suggestion is a default for the admin's folder-path field on the
ingest/review screen, pre-filled but fully editable before the source is
written — exactly how `suggested_grade` already works today. It is
never written automatically; an admin who ignores the field entirely
gets `""` (root), not whatever the Reader guessed.

## Admin UI

The admin Library page (`web/src/routes/(admin)/admin/+page.svelte`)
gains:

- A folder tree alongside the existing flat/search list — collapsible,
  derived from the distinct `folder_path` values, same place the
  existing topic/grade filters already live.
- A per-source folder field, editable from the same row-level controls
  the existing grade `<select>` and `can_upload_library` toggle already
  use (`PATCH /api/sources/{id}`, extended with a `folder_path` field,
  same route the existing title/grade edits go through).
- A move action for an existing folder (rename, or move a whole subtree
  under a different parent) — the single prefix-rewrite Cypher statement
  above, exposed as one superadmin-or-admin action, not a drag-and-drop
  tree editor (that's a real UI investment this spec doesn't assume is
  worth it yet; a plain "rename this folder" text field covers the same
  outcome).

Practitioners see the resulting folder structure read-only in
`practitioner/knowledge/+page.svelte`'s listing (same read-only
posture the existing weight-adjustment-only view already has toward
everything else about a source) — they cannot move a source or rename a
folder.

## What this does not do

- No per-folder permissions (e.g. "this practitioner can only see
  `Hormones/`") — out of scope; every source a practitioner can already
  see, they still see, just grouped.
- No nested-folder depth limit beyond what a sane UI can render; not
  enforced server-side.
