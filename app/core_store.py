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

import json
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


# --- Admins --------------------------------------------------------------

def create_admin(email: str, password_hash: str, name: str) -> dict:
    admin = {"id": str(uuid.uuid4()), "email": email,
             "password_hash": password_hash, "name": name, "created_at": _now()}
    with _connect() as conn:
        conn.execute(
            "INSERT INTO admins (id, email, password_hash, name, created_at) "
            "VALUES (:id, :email, :password_hash, :name, :created_at)",
            admin,
        )
    return admin


def get_admin_by_email(email: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM admins WHERE email = ?", (email,)
        ).fetchone()
    return dict(row) if row else None


# --- Practitioners ---------------------------------------------------------

def _decode_practitioner(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["specialties"] = json.loads(d.pop("specialties_json"))
    d["languages"] = json.loads(d.pop("languages_json"))
    return d


def create_practitioner_pending(
    email: str, password_hash: str, name: str, bio: str = "",
    specialties: list[str] | None = None, languages: list[str] | None = None,
    years_experience: int = 0, consultation_price_cents: int = 0,
) -> dict:
    practitioner_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO practitioners (id, email, password_hash, name, "
            "status, plan, bio, specialties_json, languages_json, "
            "years_experience, consultation_price_cents, created_at) "
            "VALUES (?, ?, ?, ?, 'pending', 'basic', ?, ?, ?, ?, ?, ?)",
            (practitioner_id, email, password_hash, name, bio,
             json.dumps(specialties or []), json.dumps(languages or []),
             years_experience, consultation_price_cents, _now()),
        )
    return get_practitioner(practitioner_id)


def get_practitioner(practitioner_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM practitioners WHERE id = ?", (practitioner_id,)
        ).fetchone()
    return _decode_practitioner(row) if row else None


def get_practitioner_by_email(email: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM practitioners WHERE email = ?", (email,)
        ).fetchone()
    return _decode_practitioner(row) if row else None


def list_practitioners(status: str | None = None) -> list[dict]:
    query = "SELECT * FROM practitioners"
    params: tuple = ()
    if status is not None:
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY created_at DESC"
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_decode_practitioner(r) for r in rows]


def approve_practitioner(practitioner_id: str) -> dict | None:
    with _connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM practitioners WHERE id = ?", (practitioner_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE practitioners SET status = 'approved', approved_at = ? "
            "WHERE id = ?", (_now(), practitioner_id),
        )
    log("admin", "practitioner approved", practitioner_id)
    return get_practitioner(practitioner_id)


def reject_practitioner(practitioner_id: str) -> dict | None:
    with _connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM practitioners WHERE id = ?", (practitioner_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE practitioners SET status = 'rejected' WHERE id = ?",
            (practitioner_id,),
        )
    log("admin", "practitioner rejected", practitioner_id)
    return get_practitioner(practitioner_id)


def suspend_practitioner(practitioner_id: str) -> dict | None:
    with _connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM practitioners WHERE id = ?", (practitioner_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE practitioners SET status = 'suspended' WHERE id = ?",
            (practitioner_id,),
        )
    log("admin", "practitioner suspended", practitioner_id)
    return get_practitioner(practitioner_id)


def set_plan(practitioner_id: str, plan: str) -> dict | None:
    if plan not in PLANS:
        raise ValueError(f"unknown plan: {plan}")
    with _connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM practitioners WHERE id = ?", (practitioner_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE practitioners SET plan = ? WHERE id = ?",
            (plan, practitioner_id),
        )
    log("admin", "practitioner plan changed", f"{practitioner_id} -> {plan}")
    return get_practitioner(practitioner_id)


def update_practitioner_profile(practitioner_id: str, **fields) -> dict | None:
    allowed = {"name", "bio", "specialties", "languages", "years_experience",
               "consultation_price_cents", "photo_path"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"unknown profile field(s): {', '.join(sorted(unknown))}")
    if not fields:
        return get_practitioner(practitioner_id)
    columns = {}
    for key, value in fields.items():
        if key in ("specialties", "languages"):
            columns[f"{key}_json"] = json.dumps(value)
        else:
            columns[key] = value
    set_clause = ", ".join(f"{col} = ?" for col in columns)
    with _connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM practitioners WHERE id = ?", (practitioner_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            f"UPDATE practitioners SET {set_clause} WHERE id = ?",
            (*columns.values(), practitioner_id),
        )
    return get_practitioner(practitioner_id)


def set_practitioner_api_key(practitioner_id: str, encrypted_key: str | None) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE practitioners SET anthropic_api_key_encrypted = ? WHERE id = ?",
            (encrypted_key, practitioner_id),
        )


def set_stripe_fields(
    practitioner_id: str, customer_id: str | None = None,
    subscription_id: str | None = None, status: str | None = None,
) -> dict | None:
    updates = {}
    if customer_id is not None:
        updates["stripe_customer_id"] = customer_id
    if subscription_id is not None:
        updates["stripe_subscription_id"] = subscription_id
    if status is not None:
        updates["stripe_status"] = status
    if not updates:
        return get_practitioner(practitioner_id)
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    with _connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM practitioners WHERE id = ?", (practitioner_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            f"UPDATE practitioners SET {set_clause} WHERE id = ?",
            (*updates.values(), practitioner_id),
        )
    return get_practitioner(practitioner_id)


def activate_pro(practitioner_id: str) -> dict:
    """Flip the plan to pro and make sure a vault file exists.

    Idempotent: if data/vaults/<id>.db already exists (e.g. a downgrade
    followed by re-upgrade), it is reused rather than recreated.
    """
    practitioner = set_plan(practitioner_id, "pro")
    if practitioner is None:
        raise ValueError(f"unknown practitioner: {practitioner_id}")
    vault_path = Path(cfg.vaults_path) / f"{practitioner_id}.db"
    if not vault_path.exists():
        # Deferred import: vault.py may not exist yet when this module is
        # authored/run in parallel with it, same reasoning as auth.py.
        from . import vault
        vault.ensure_schema(practitioner_id)
    return practitioner


# --- Contact forms -----------------------------------------------------------

def create_contact_submission(
    practitioner_id: str, client_name: str, client_email: str, message: str,
) -> dict:
    submission = {
        "id": str(uuid.uuid4()), "practitioner_id": practitioner_id,
        "client_name": client_name, "client_email": client_email,
        "message": message, "status": "new", "created_at": _now(),
    }
    with _connect() as conn:
        conn.execute(
            "INSERT INTO contact_form_submissions (id, practitioner_id, "
            "client_name, client_email, message, status, created_at) "
            "VALUES (:id, :practitioner_id, :client_name, :client_email, "
            ":message, :status, :created_at)",
            submission,
        )
    log("client", "contact submission received", practitioner_id)
    return submission


def list_contact_submissions(
    practitioner_id: str | None = None, status: str | None = None,
) -> list[dict]:
    where, params = [], []
    if practitioner_id:
        where.append("practitioner_id = ?")
        params.append(practitioner_id)
    if status:
        where.append("status = ?")
        params.append(status)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM contact_form_submissions {clause} "
            "ORDER BY created_at DESC",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def update_contact_status(submission_id: str, status: str) -> dict | None:
    if status not in ("new", "contacted", "closed"):
        raise ValueError(f"unknown status: {status}")
    with _connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM contact_form_submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE contact_form_submissions SET status = ? WHERE id = ?",
            (status, submission_id),
        )
        row = conn.execute(
            "SELECT * FROM contact_form_submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()
    return dict(row)


# --- Analytics ---------------------------------------------------------------

def log_profile_view(practitioner_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO profile_view_events (id, practitioner_id, ts) "
            "VALUES (?, ?, ?)",
            (str(uuid.uuid4()), practitioner_id, _now()),
        )


def site_stats() -> dict:
    with _connect() as conn:
        views = conn.execute(
            "SELECT count(*) FROM profile_view_events"
        ).fetchone()[0]
        contacts = conn.execute(
            "SELECT count(*) FROM contact_form_submissions"
        ).fetchone()[0]
    return {"total_views": views, "total_contacts": contacts}


def practitioner_stats(practitioner_id: str) -> dict:
    with _connect() as conn:
        views = conn.execute(
            "SELECT count(*) FROM profile_view_events WHERE practitioner_id = ?",
            (practitioner_id,),
        ).fetchone()[0]
        contacts = conn.execute(
            "SELECT count(*) FROM contact_form_submissions "
            "WHERE practitioner_id = ?",
            (practitioner_id,),
        ).fetchone()[0]
    return {"views": views, "contacts": contacts}


# --- Questionnaires (versioned) -----------------------------------------------

def _decode_question(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["options"] = json.loads(d.pop("options_json"))
    return d


def _insert_questionnaire(
    title: str, version: int, created_by: str, questions: list[dict],
) -> str:
    """Insert a new questionnaire version and deactivate every other one —
    only one questionnaire is active at a time."""
    questionnaire_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute("UPDATE questionnaires SET is_active = 0")
        conn.execute(
            "INSERT INTO questionnaires (id, title, version, is_active, "
            "created_by, created_at) VALUES (?, ?, ?, 1, ?, ?)",
            (questionnaire_id, title, version, created_by, _now()),
        )
        for ordinal, q in enumerate(questions):
            conn.execute(
                "INSERT INTO questionnaire_questions (id, questionnaire_id, "
                "ordinal, prompt, input_type, options_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), questionnaire_id, ordinal, q["prompt"],
                 q["input_type"], json.dumps(q.get("options", []))),
            )
    return questionnaire_id


def create_questionnaire(title: str, questions: list[dict], created_by: str) -> dict:
    questionnaire_id = _insert_questionnaire(title, 1, created_by, questions)
    log(created_by, "questionnaire created", questionnaire_id)
    return get_questionnaire(questionnaire_id)


def edit_questionnaire(
    questionnaire_id: str, title: str, questions: list[dict], created_by: str,
) -> dict:
    """Create a new version rather than mutate the one clients already
    answered against; _insert_questionnaire flips the old version's
    is_active off as part of the single-active-version invariant."""
    with _connect() as conn:
        old = conn.execute(
            "SELECT version FROM questionnaires WHERE id = ?",
            (questionnaire_id,),
        ).fetchone()
    if old is None:
        raise ValueError(f"unknown questionnaire: {questionnaire_id}")
    new_id = _insert_questionnaire(title, old["version"] + 1, created_by, questions)
    log(created_by, "questionnaire edited", f"{questionnaire_id} -> {new_id}")
    return get_questionnaire(new_id)


def get_active_questionnaire() -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM questionnaires WHERE is_active = 1"
        ).fetchone()
    return get_questionnaire(row["id"]) if row else None


def get_questionnaire(questionnaire_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM questionnaires WHERE id = ?", (questionnaire_id,)
        ).fetchone()
        if row is None:
            return None
        questions = conn.execute(
            "SELECT * FROM questionnaire_questions WHERE questionnaire_id = ? "
            "ORDER BY ordinal",
            (questionnaire_id,),
        ).fetchall()
    return {**dict(row), "questions": [_decode_question(q) for q in questions]}


def list_questionnaires() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM questionnaires ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# --- Client directory (routing pointer only) ----------------------------------

def add_client_directory_entry(
    email: str, practitioner_id: str, client_id: str,
) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO client_directory "
            "(email, practitioner_id, client_id) VALUES (?, ?, ?)",
            (email, practitioner_id, client_id),
        )


def get_client_directory_entry(email: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM client_directory WHERE email = ?", (email,)
        ).fetchone()
    return dict(row) if row else None
