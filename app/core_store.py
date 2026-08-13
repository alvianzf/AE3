"""The core store: shared, cross-tenant data — practitioners, plans, contact
forms, questionnaires, site stats, and the two tables the v2 spec's schema
table doesn't name but real login requires:

- `admins`: the spec says admin has its own credentials but never says where
  an admin account lives; `practitioners` doesn't fit (it carries plan and
  public-profile fields that make no sense for an admin).
- `client_directory`: clients live entirely inside their practitioner's
  vault (correctly — that's the isolation boundary), but a login request
  arrives with just an email and needs to know which vault file to open
  before any vault can be queried. This table is a routing pointer only,
  never clinical content.

Same shape as app/patients.py: a fresh connection per call, idempotent
schema, plain module-level functions.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import get_config

cfg = get_config()

STATUSES = ("pending", "approved", "rejected", "suspended")
PLANS = ("basic", "pro")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    path = Path(cfg.core_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS practitioners (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                plan TEXT NOT NULL DEFAULT 'basic',
                photo_path TEXT,
                bio TEXT NOT NULL DEFAULT '',
                specialties_json TEXT NOT NULL DEFAULT '[]',
                languages_json TEXT NOT NULL DEFAULT '[]',
                years_experience INTEGER NOT NULL DEFAULT 0,
                consultation_price_cents INTEGER NOT NULL DEFAULT 0,
                anthropic_api_key_encrypted TEXT,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                stripe_status TEXT,
                created_at TEXT NOT NULL,
                approved_at TEXT
            );
            CREATE INDEX IF NOT EXISTS practitioners_by_status
                ON practitioners(status);

            -- Routing only: which vault a client's login belongs to. No
            -- clinical content — that lives in the vault itself.
            CREATE TABLE IF NOT EXISTS client_directory (
                email TEXT PRIMARY KEY,
                practitioner_id TEXT NOT NULL,
                client_id TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS contact_form_submissions (
                id TEXT PRIMARY KEY,
                practitioner_id TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_email TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS contacts_by_practitioner
                ON contact_form_submissions(practitioner_id, created_at);

            CREATE TABLE IF NOT EXISTS questionnaires (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                version INTEGER NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS questionnaire_questions (
                id TEXT PRIMARY KEY,
                questionnaire_id TEXT NOT NULL REFERENCES questionnaires(id),
                ordinal INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                input_type TEXT NOT NULL,
                options_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE INDEX IF NOT EXISTS questions_by_questionnaire
                ON questionnaire_questions(questionnaire_id, ordinal);

            -- One row per directory/coach-detail-page render.
            CREATE TABLE IF NOT EXISTS profile_view_events (
                id TEXT PRIMARY KEY,
                practitioner_id TEXT NOT NULL,
                ts TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS views_by_practitioner
                ON profile_view_events(practitioner_id, ts);

            -- Admin/practitioner actions on shared data only: approvals,
            -- plan changes, library edits, questionnaire edits. Never a
            -- client name or clinical content — that boundary lives in each
            -- vault's own audit_events, same rule v1 drew for patients.
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                ts TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS core_audit_by_ts ON audit_events(ts);
            """
        )


def ping() -> bool:
    with _connect() as conn:
        conn.execute("SELECT 1")
    return True


def log(actor: str, action: str, detail: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO audit_events (id, ts, actor, action, detail) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), _now(), actor, action, detail),
        )
