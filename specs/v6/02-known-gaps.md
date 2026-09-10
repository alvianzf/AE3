# 02 · Known gaps and follow-up work

## Schema-per-practitioner is a weaker isolation boundary than separate files

Stated plainly in `DEPLOY.md`'s Postgres section too, repeated here
because it's the single most important thing to know before trusting
this with real patient data: the old design's per-practitioner
*SQLite file* meant a bug could not leak one practitioner's data into
another's query without an actual file-path mistake — a structurally
hard error to make silently. The new design's per-practitioner *Postgres
schema* is enforced by `search_path`, which is a session-level setting a
sufficiently-wrong piece of code (raw SQL with an interpolated schema
name from the wrong source, a connection-pool bug that fails to reset
`search_path` between requests, a Postgres role misconfiguration) could
violate without an obviously-wrong file path to catch it. `app/db.py`'s
`vault_connection()` resets `search_path` to `public` in its `finally`
block specifically to close the "returned to the pool with an old
practitioner's search_path still set" failure mode — but this class of
protection is defense-in-depth, not the same category of guarantee a
separate file gave for free. **Worth a real security review before
production patient data goes anywhere near this**, not assumed
equivalent by default.

## Connection pool sizing is a starting guess

`POSTGRES_POOL_MAX` defaults to 20 (`app/config.py`). Every
`vault_connection()` call also pays a `CREATE SCHEMA IF NOT EXISTS` +
`SET search_path` round trip even when the schema already exists — cheap
per call, but not free, and not benchmarked under concurrent load. If
this becomes a real bottleneck, caching "schema already exists" per
practitioner (instead of re-checking every call) is the natural fix, not
done here.

## `data/core.db` was empty in this environment

This repo's dev sandbox had a 0-byte `data/core.db` with no tables (never
actually populated — the app hadn't been run as a live server against
the old SQLite core store in this environment). The migration script
handles a missing/empty source file gracefully (logs and skips), but that
also means **the core-store migration path itself was only exercised
against an empty source**, not a populated one — the practitioner-vault
migration path is the one that actually moved real rows and was verified
end-to-end. If a real deployment's `core.db` has actual practitioner/
admin/questionnaire data, running `--dry-run` first (as `DEPLOY.md`
instructs) before the real migration is the safety net, not just a
suggestion.

## What this migration didn't touch

- The `anthropic_api_key_encrypted` column, already vestigial since
  [v4.2](../v4.2/README.md) retired the BYO-key model — carried forward
  into the new `practitioners` table schema as-is (unused, not read or
  written by any code path), not cleaned up here either.
- `data/patients.db` — confirmed vestigial (no current code reads
  `SQLITE_PATH`/`sqlite_path` at all; it's a leftover from an even
  earlier version, per `app/core_store.py`'s own docstring reference to
  "`app/patients.py`"). Left alone, not migrated, not deleted.
- Any change to the actual production server — this spec's `DEPLOY.md`
  additions are instructions for the next deploy to follow, not
  something executed against the live host.
