"""Postgres connection layer, replacing sqlite3 across app/core_store.py
and app/vault.py (specs/v6 — see that folder for the migration write-up).

Three connection helpers, matching the isolation shapes the app has
always had, all built on one shared pooled-connection skeleton
(`_pooled_connection`) rather than three independent hand-rolled copies
of the same checkout/commit/rollback/cleanup sequence:

- `core_connection()` — the shared store (practitioners, admins,
  questionnaires, site stats). One schema (`public`), one pool.
- `vault_connection(practitioner_id)` — a practitioner's vault. Same
  physical Postgres instance and database as the core store now (that's
  the whole point of this migration), but **kept in its own Postgres
  schema per practitioner** (`vault_<uuid>`) rather than collapsed into
  shared tables — preserving the isolation property the old
  one-SQLite-file-per-practitioner design had on purpose
  (specs/v1/07-security.md, "the leak that was found"). A query that
  doesn't explicitly cross schemas structurally cannot see another
  practitioner's rows, same guarantee as before, enforced by Postgres's
  schema/search_path mechanism instead of the filesystem.
- `schema_connection(schema_name)` — like vault_connection(), but scoped
  directly to an already-known Postgres schema name (from
  list_vault_schemas()) rather than derived from a practitioner_id — the
  schema-name sanitization in vault_schema_name() is one-way, so a schema
  found this way can't be reliably mapped back to the practitioner_id
  that created it.

All three hand back a thin wrapper (`_Conn`) whose `.execute()` mimics
`sqlite3.Connection.execute()`'s shorthand (build a cursor, run the
query, return it) so the ported code in core_store.py/vault.py stays
close to its original shape — the diff that matters is `?` → `%s`
placeholders and a few dict-vs-tuple row-access spots, not a wholesale
restructuring of every function.
"""
from __future__ import annotations

import re
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

from .config import get_config

cfg = get_config()

_pool: ThreadedConnectionPool | None = None


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(
            1, cfg.postgres_pool_max,
            host=cfg.postgres_host, port=cfg.postgres_port,
            user=cfg.postgres_user, password=cfg.postgres_password,
            dbname=cfg.postgres_database,
        )
    return _pool


class _Conn:
    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql: str, params=None):
        cur = self._raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, seq_of_params) -> None:
        cur = self._raw.cursor()
        cur.executemany(sql, seq_of_params)
        cur.close()

    def executescript(self, sql: str) -> None:
        # No sqlite3-style multi-statement convenience in psycopg2 needed —
        # a plain cursor.execute() already runs a semicolon-separated
        # script as one round trip against Postgres.
        cur = self._raw.cursor()
        cur.execute(sql)
        cur.close()


@contextmanager
def _pooled_connection(setup_sql: str | None = None):
    """Check out a pooled connection, optionally run `setup_sql` (schema
    creation / search_path), yield a _Conn, commit on success / rollback
    on exception — then always reset search_path back to `public` and
    return the connection to the pool with no open transaction.

    That reset runs even for a connection whose search_path was never
    changed (core_connection()) so every caller shares one cleanup path
    instead of three independently-verified ones. It matters for real:
    the reset statement itself opens a fresh implicit transaction on this
    non-autocommit connection, and leaving that uncommitted would return
    the connection to the pool "idle in transaction" for the next caller
    to inherit — so the reset is followed by its own commit(), not
    assumed to be covered by the commit()/rollback() above (which already
    ran before this statement).
    """
    pool = _get_pool()
    raw = pool.getconn()
    try:
        if setup_sql:
            setup = raw.cursor()
            setup.execute(setup_sql)
            setup.close()
        yield _Conn(raw)
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        reset = raw.cursor()
        reset.execute("SET search_path TO public")
        reset.close()
        raw.commit()
        pool.putconn(raw)


def core_connection():
    return _pooled_connection()


_SCHEMA_UNSAFE = re.compile(r"[^a-z0-9_]")


def vault_schema_name(practitioner_id: str) -> str:
    # practitioner_id is always a uuid4 string in practice, but this can't
    # be parameterized (it's used in SET search_path / CREATE SCHEMA, not
    # a query value) — sanitize defensively rather than trust the caller.
    safe = _SCHEMA_UNSAFE.sub("_", practitioner_id.lower())
    return f"vault_{safe}"


def vault_connection(practitioner_id: str):
    schema = vault_schema_name(practitioner_id)
    return _pooled_connection(
        f'CREATE SCHEMA IF NOT EXISTS "{schema}"; SET search_path TO "{schema}", public'
    )


def schema_connection(schema_name: str):
    return _pooled_connection(f'SET search_path TO "{schema_name}", public')


def list_vault_schemas() -> list[str]:
    """Every vault_* schema that actually exists in Postgres — used for
    boot-time repair (app/main.py) so a schema whose owning practitioner
    row is missing or stale from core_store still gets its DDL re-run,
    not just the schemas derivable from today's practitioners list."""
    with core_connection() as conn:
        rows = conn.execute(
            "SELECT schema_name FROM information_schema.schemata "
            r"WHERE schema_name LIKE 'vault\_%' ESCAPE '\'"
        ).fetchall()
    return [r["schema_name"] for r in rows]
