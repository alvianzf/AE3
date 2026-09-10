"""Postgres connection layer, replacing sqlite3 across app/core_store.py
and app/vault.py (specs/v6 — see that folder for the migration write-up).

Two connection helpers, matching the two isolation shapes the app has
always had:

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

Both context managers hand back a thin wrapper (`_Conn`) whose
`.execute()` mimics `sqlite3.Connection.execute()`'s shorthand (build a
cursor, run the query, return it) so the ported code in core_store.py/
vault.py stays close to its original shape — the diff that matters is
`?` → `%s` placeholders and a few dict-vs-tuple row-access spots, not a
wholesale restructuring of every function.
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
def core_connection():
    pool = _get_pool()
    raw = pool.getconn()
    try:
        yield _Conn(raw)
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        pool.putconn(raw)


_SCHEMA_UNSAFE = re.compile(r"[^a-z0-9_]")


def vault_schema_name(practitioner_id: str) -> str:
    # practitioner_id is always a uuid4 string in practice, but this can't
    # be parameterized (it's used in SET search_path / CREATE SCHEMA, not
    # a query value) — sanitize defensively rather than trust the caller.
    safe = _SCHEMA_UNSAFE.sub("_", practitioner_id.lower())
    return f"vault_{safe}"


@contextmanager
def vault_connection(practitioner_id: str):
    pool = _get_pool()
    raw = pool.getconn()
    schema = vault_schema_name(practitioner_id)
    try:
        setup = raw.cursor()
        setup.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        setup.execute(f'SET search_path TO "{schema}", public')
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
        pool.putconn(raw)
