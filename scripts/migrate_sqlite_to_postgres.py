#!/usr/bin/env python3
"""One-time data migration: the old SQLite stores -> the new Postgres
layout (specs/v6). Copies rows as-is (same ids, same timestamps) — this
is a data copy, not a re-derivation, so every foreign key (session_id,
client_id, ...) stays consistent across tables exactly as it was.

Idempotent: every insert is ON CONFLICT DO NOTHING, so re-running this
after a partial failure only fills in what's missing, never duplicates.

Usage:
    python scripts/migrate_sqlite_to_postgres.py
    python scripts/migrate_sqlite_to_postgres.py --dry-run

Reads paths from the same env vars app/config.py already uses for the
pre-migration SQLite layout (CORE_DB_PATH, VAULTS_PATH) and writes to
the Postgres connection app/db.py is configured for (POSTGRES_*). Safe
to run against an empty/missing source (skips with a log line, not an
error) — this repo's dev environment, for instance, has no core.db yet.
"""
from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# (table, columns-in-insert-order, bool-columns-to-coerce)
CORE_TABLES = [
    ("admins", ["id", "email", "password_hash", "name", "role", "is_active", "created_at"], ["is_active"]),
    ("practitioners", [
        "id", "email", "password_hash", "name", "status", "plan", "photo_path", "bio",
        "specialties_json", "languages_json", "years_experience", "consultation_price_cents",
        "anthropic_api_key_encrypted", "stripe_customer_id", "stripe_subscription_id",
        "stripe_status", "created_at", "approved_at",
    ], []),
    ("client_directory", ["email", "practitioner_id", "client_id"], []),
    ("contact_form_submissions", [
        "id", "practitioner_id", "client_name", "client_email", "message", "status", "created_at",
    ], []),
    ("questionnaires", ["id", "title", "version", "is_active", "created_by", "created_at"], ["is_active"]),
    ("questionnaire_questions", [
        "id", "questionnaire_id", "ordinal", "prompt", "input_type", "options_json", "theme",
    ], []),
    ("profile_view_events", ["id", "practitioner_id", "ts"], []),
    ("audit_events", ["id", "ts", "actor", "action", "detail"], []),
    ("staged_sources", [
        "id", "kind", "filename", "source_url", "media_type", "pages_json",
        "char_count", "page_count", "created_at", "created_by",
    ], []),
]

VAULT_TABLES = [
    ("clients", [
        "id", "name", "email", "password_hash", "password_set", "dob", "country", "created_at",
    ], ["password_set"]),
    ("record_entries", ["id", "client_id", "kind", "content", "created_at", "session_id"], []),
    ("audit_events", ["id", "ts", "actor", "action", "detail", "client_id"], []),
    ("sessions", ["id", "client_id", "title", "started_at", "status"], []),
    ("session_documents", [
        "id", "session_id", "client_id", "kind", "status", "content", "updated_at",
    ], []),
    ("intake_notes", ["client_id", "theme", "note", "updated_at"], []),
    ("source_weights", ["source_id", "weight", "updated_at"], []),
    ("session_turns", ["id", "session_id", "ordinal", "question", "answer", "payload", "created_at"], []),
    ("questionnaire_responses", [
        "id", "client_id", "questionnaire_id", "questionnaire_version",
        "answers_json", "submitted_at", "viewed_at",
    ], []),
    ("uploaded_files", [
        "id", "client_id", "original_name", "media_type", "storage_path", "uploaded_at",
    ], []),
    ("wearable_connections", ["id", "client_id", "provider", "status", "connected_at"], []),
    ("wearable_data_points", [
        "id", "client_id", "provider", "metric", "value", "recorded_at",
    ], []),
]


def _sqlite_rows(db_path: Path, table: str) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            return []
        return conn.execute(f"SELECT * FROM {table}").fetchall()
    finally:
        conn.close()


def _copy_table(pg_conn, source_rows, table: str, columns: list[str],
                bool_columns: list[str], dry_run: bool) -> int:
    if not source_rows:
        return 0
    placeholders = ", ".join(f"%({c})s" for c in columns)
    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
        "ON CONFLICT DO NOTHING"
    )
    rows = []
    for r in source_rows:
        row = {}
        for c in columns:
            v = r[c] if c in r.keys() else None
            if c in bool_columns:
                v = bool(v)
            row[c] = v
        rows.append(row)
    if dry_run:
        logging.info("  [dry-run] would insert %d row(s) into %s", len(rows), table)
        return len(rows)
    cur = pg_conn.cursor()
    for row in rows:
        cur.execute(sql, row)
    n = cur.rowcount
    cur.close()
    logging.info("  %s: %d row(s) migrated (source had %d)", table, len(rows), len(source_rows))
    return len(rows)


def migrate_core(cfg, dry_run: bool) -> None:
    from app.db import core_connection

    path = Path(cfg.core_db_path)
    if not path.exists():
        logging.info("No core SQLite DB at %s — nothing to migrate for the core store.", path)
        return
    logging.info("Migrating core store from %s", path)
    with core_connection() as conn:
        from app import core_store
        core_store.ensure_schema()
        for table, columns, bool_cols in CORE_TABLES:
            rows = _sqlite_rows(path, table)
            _copy_table(conn._raw, rows, table, columns, bool_cols, dry_run)


def migrate_vaults(cfg, dry_run: bool) -> None:
    from app.db import vault_connection

    vaults_dir = Path(cfg.vaults_path)
    if not vaults_dir.exists():
        logging.info("No vaults directory at %s — nothing to migrate for practitioner vaults.",
                     vaults_dir)
        return
    db_files = sorted(vaults_dir.glob("*.db"))
    if not db_files:
        logging.info("No vault .db files found under %s.", vaults_dir)
        return
    from app import vault
    for db_file in db_files:
        practitioner_id = db_file.stem
        logging.info("Migrating vault for practitioner %s from %s", practitioner_id, db_file)
        with vault_connection(practitioner_id) as conn:
            if not dry_run:
                vault.ensure_schema(practitioner_id)
            for table, columns, bool_cols in VAULT_TABLES:
                rows = _sqlite_rows(db_file, table)
                _copy_table(conn._raw, rows, table, columns, bool_cols, dry_run)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="count what would be migrated, write nothing")
    args = parser.parse_args()

    from app.config import get_config
    cfg = get_config()

    logging.info("=== Core store ===")
    migrate_core(cfg, args.dry_run)
    logging.info("=== Practitioner vaults ===")
    migrate_vaults(cfg, args.dry_run)
    logging.info("Done.")


if __name__ == "__main__":
    main()
