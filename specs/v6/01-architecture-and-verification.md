# 01 · Architecture and what was actually verified

## The schema-per-practitioner design

`app/db.py` has two connection helpers, matching the two isolation shapes
the app already had:

- `core_connection()` — the shared store, `public` schema, one pool.
- `vault_connection(practitioner_id)` — creates `vault_<id>` (a
  sanitized version of the practitioner's id) if it doesn't exist,
  `SET search_path` to it, hands back a connection scoped to exactly that
  practitioner's tables, resets `search_path` back to `public` on the way
  out (the connection returns to the pool and could be reused by a
  different practitioner's request next).

Both return a thin `_Conn` wrapper whose `.execute()` mimics
`sqlite3.Connection.execute()`'s shorthand (build a cursor, run the
query, return it, using `psycopg2.extras.RealDictCursor` so rows stay
dict-like — `row["field"]` and `dict(row)` both keep working exactly as
they did against `sqlite3.Row`). This is why `core_store.py`/`vault.py`'s
diff against their SQLite originals is mostly `?` → `%s` placeholders and
a handful of `count(*)` queries needing an explicit `AS n` alias (`
RealDictCursor` rows aren't index-subscriptable the way `sqlite3.Row`
partially is) — not a wholesale restructuring.

## What actually ran, live, against a real Postgres instance

Unlike this session's other large changes (v4.2, v5 — both explicitly
"code-confirmed only, not live-verified" since no live Nebius/Neo4j
access existed), **this migration had a real, local Postgres instance
available** (installed via Homebrew, isolated on port 5433 from an
unrelated pre-existing system Postgres 17 install found on the same
machine — see the commit message for why a fresh instance was set up
instead of reusing that one). So this was actually exercised, not just
read for correctness:

- `core_store.ensure_schema()` + `ping()` + full CRUD round-trips for
  admins, practitioners (including the specialties/languages JSON
  encode/decode), questionnaires (including the
  create-deactivates-the-old-one invariant), staged sources, and the
  `client_directory`'s `ON CONFLICT ... DO UPDATE` upsert.
- `vault.ensure_schema()` + a full client lifecycle: create, add
  `condition`/`medication`/`lab` entries, create a session, add a turn,
  read it back, set a source weight, delete the client (cascade).
- **Schema isolation itself**, confirmed by inspecting Postgres directly
  (`\dn`) — two different `practitioner_id`s produced two genuinely
  separate schemas (`vault_test_practitioner_1`, and later the real
  migrated practitioner's `vault_e346d6e0_...`), not shared tables with a
  tenant column.
- `auth.ensure_bootstrap_admin()` end-to-end, including password
  verification against the Postgres-stored hash.
- `app/main.py`'s full module body importing and executing cleanly
  (same residual failure as every other stage this session — the
  unrelated missing `web-build/_app` directory in this dev sandbox, not
  a code defect).
- `scripts/migrate_sqlite_to_postgres.py`, both `--dry-run` and for
  real, against this repo's one actual pre-existing vault file
  (`data/vaults/e346d6e0-89e8-48cb-99a4-9e7763c767ec.db` — 1 real client,
  1 real audit event), with the migrated rows spot-checked directly in
  Postgres afterward. `data/core.db` turned out to be an empty (0-byte)
  file with no tables — nothing to migrate there in this environment.

## What's still only code-reviewed, not live-run

- **The production deploy path** (`DEPLOY.md`'s new Postgres section) —
  written from the same reasoning as the rest of that document's
  existing sections, not executed against the actual production server.
- **Concurrent/multi-connection-pool behavior under real load** — the
  `ThreadedConnectionPool` sizing (`POSTGRES_POOL_MAX`, default 20) is a
  reasonable starting value, not load-tested.
- **Every other module's SQL-adjacent code paths that weren't directly
  exercised** by the manual smoke tests above (e.g. `billing.py`'s Stripe
  field updates, `wearables.py`'s connection flow beyond what
  `vault.create_wearable_connection`/`seed_fixture_wearable_data` cover
  directly) — these call through to the same ported functions, so the
  underlying query logic was verified, but the full FastAPI route wiring
  around them wasn't clicked through in a running server.
