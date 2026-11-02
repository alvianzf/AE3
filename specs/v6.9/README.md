# v6.9 — Private knowledge base, per-practitioner access

**Status: implemented.**

An admin can mark a document — or a whole folder (`v6.8/01`) at once, via
bulk-select — as private. A private document is invisible to every
practitioner's RAG results (seed search and graph traversal both) except
the specific ones the admin has explicitly granted access to.

- [**01 · Private knowledge base**](01-private-knowledge-base.md) — the
  full spec: data model, where enforcement actually has to live (every
  retrieval path a document can reach a consult through, not just one),
  the admin bulk-select/grant UI, and the explicit tradeoff in how
  "privatize a folder" interacts with `v6.8/01`'s folder model (a path
  prefix, not a first-class node).

## Baseline this builds on

- `v6.8/01`'s folder model (`Document.folder_path`, a plain string
  prefix) — bulk-privatizing "a folder" is the same prefix-match bulk
  write `rename_folder()` already does, not new machinery.
- `app/vault.py`'s per-practitioner `source_weights` and
  `core_store.py`'s `can_upload_library` are the two existing precedents
  for "a document- or practitioner-scoped override, checked at request
  time, not cached" — access grants follow the same shape, as a new
  core-store table (an *admin* grant, not something a practitioner sets
  about themselves, so it does not live in a per-practitioner vault
  schema the way `source_weights` does).

## What this does not change

No change to the existing shared-grade/`min_grade` filtering — privacy is
an independent, additional gate layered alongside it at the same call
sites, not a replacement for it.
