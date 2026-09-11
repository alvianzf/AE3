# v6 — SQLite → Postgres, schema-per-practitioner

**Status: implemented and live-verified locally** (not the usual
code-confirmed-only caveat this session's other big changes carry — every
function in this migration was actually run against a real local
Postgres instance, including a real end-to-end data migration of this
repo's one existing practitioner vault. See
[01](01-architecture-and-verification.md) for exactly what was run).

Replaces the app's two SQLite stores — `app/core_store.py` (one shared
file, `data/core.db`) and `app/vault.py` (one file per Pro practitioner,
`data/vaults/<id>.db`) — with a single Postgres database, using
**Postgres schemas to preserve the per-practitioner isolation** the
separate-file design had on purpose. Both modules keep their exact public
function signatures and return shapes, so nothing else in the app —
`auth.py`, `main.py`, `billing.py`, `wearables.py`, `uploads.py` — needed
to change.

## Docs

- [**01 · Architecture and what was actually verified**](01-architecture-and-verification.md) —
  the schema-per-practitioner design, `app/db.py`'s connection layer, and
  a precise account of what ran live vs. what's still only code-reviewed.
- [**02 · Known gaps and follow-up work**](02-known-gaps.md) — the
  isolation-boundary security note (also in `DEPLOY.md`), connection
  pool sizing, and what this migration deliberately didn't touch.

## What this doesn't change

Neo4j (the knowledge graph, [v5](../v5/README.md)) and Nebius (the LLM
provider, [v4.2](../v4.2/README.md)) are unaffected — this is scoped to
the two SQLite stores only, per the explicit scope decision (asked and
answered): migrate everything, preserve isolation via schema-per-tenant,
and also cover production deploy config (`DEPLOY.md`).
