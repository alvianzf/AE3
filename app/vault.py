"""The client vault: one SQLite file per Pro practitioner.

Same schema and behavior as v1's single global patient vault (app/patients.py),
except every function is scoped to a practitioner_id and resolves its own
SQLite file under cfg.vaults_path instead of a single module-global path.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import get_config

cfg = get_config()

KINDS = ("lab", "history", "note", "session_summary")

WEARABLE_PROVIDERS = ("oura", "whoop", "garmin")

# Fixture stand-in for a live vendor pull. v2 seeds representative sample
# metrics on connect rather than calling out to Oura/Whoop/Garmin — see
# specs/v2/06-client-portal.md ("what's not real yet"). Swapping this for a
# real pull later is app/wearables.py's job, not this dict's.
FIXTURE_WEARABLE_METRICS = {
    "oura": [
        ("sleep_score", 82),
        ("hrv", 54),
        ("resting_heart_rate", 58),
        ("readiness_score", 76),
    ],
    "whoop": [
        ("recovery_score", 68),
        ("hrv", 49),
        ("strain", 11.4),
        ("sleep_performance", 79),
    ],
    "garmin": [
        ("steps", 8420),
        ("sleep_score", 74),
        ("resting_heart_rate", 61),
        ("stress_level", 32),
    ],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect(practitioner_id: str) -> sqlite3.Connection:
    path = Path(cfg.vaults_path) / f"{practitioner_id}.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(practitioner_id: str) -> None:
    with _connect(practitioner_id) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                password_set INTEGER NOT NULL DEFAULT 1,
                dob TEXT,
                country TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS record_entries (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL REFERENCES clients(id),
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS entries_by_client
                ON record_entries(client_id, created_at);
            -- Audit of anything that touches a client. Kept here rather than in
            -- the core store because these rows carry clinical detail (the
            -- question asked, which client it was about), and that must not
            -- leave the vault.
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                ts TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT NOT NULL,
                client_id TEXT
            );
            CREATE INDEX IF NOT EXISTS audit_by_ts ON audit_events(ts);
            -- A consultation is a conversation, not a single question. Sessions
            -- and their turns live in the vault: the questions asked and answers
            -- given are clinical detail about this client.
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                title TEXT NOT NULL,
                started_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'in_progress'
            );
            CREATE INDEX IF NOT EXISTS sessions_by_client
                ON sessions(client_id, started_at);
            -- One clinician note + one client report per session, each with
            -- its own draft/final state — these are separate documents, not
            -- alternate views of the same text.
            CREATE TABLE IF NOT EXISTS session_documents (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                client_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                content TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                UNIQUE(session_id, kind)
            );
            CREATE INDEX IF NOT EXISTS documents_by_client
                ON session_documents(client_id, updated_at);
            -- A clinician's freeform note per intake theme for a client —
            -- separate from the client's own questionnaire answers.
            CREATE TABLE IF NOT EXISTS intake_notes (
                client_id TEXT NOT NULL,
                theme TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                PRIMARY KEY (client_id, theme)
            );
            -- A practitioner's own personal weight for a shared library
            -- source — never touches the admin-set grade on the Source node
            -- itself, and invisible to every other practitioner and admin.
            CREATE TABLE IF NOT EXISTS source_weights (
                source_id TEXT PRIMARY KEY,
                weight INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS session_turns (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS turns_by_session
                ON session_turns(session_id, ordinal);
            CREATE TABLE IF NOT EXISTS questionnaire_responses (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                questionnaire_id TEXT NOT NULL,
                questionnaire_version INTEGER NOT NULL,
                answers_json TEXT NOT NULL,
                submitted_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS responses_by_client
                ON questionnaire_responses(client_id, submitted_at);
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                original_name TEXT NOT NULL,
                media_type TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS files_by_client
                ON uploaded_files(client_id, uploaded_at);
            CREATE TABLE IF NOT EXISTS wearable_connections (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                connected_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS connections_by_client
                ON wearable_connections(client_id, provider);
            CREATE TABLE IF NOT EXISTS wearable_data_points (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                recorded_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS data_points_by_client
                ON wearable_data_points(client_id, recorded_at);
            """
        )
        # Migration for vaults created before password_set existed —
        # CREATE TABLE IF NOT EXISTS above doesn't add columns to an
        # existing table. Default is 1 (already-active): every real client
        # in an existing vault got their password some other way already,
        # so treating them as "still pending signup" would be the wrong
        # default, not a safe one.
        cols = {row[1] for row in conn.execute("PRAGMA table_info(clients)")}
        if "password_set" not in cols:
            conn.execute(
                "ALTER TABLE clients ADD COLUMN password_set INTEGER NOT NULL DEFAULT 1")
        session_cols = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
        if "status" not in session_cols:
            conn.execute(
                "ALTER TABLE sessions ADD COLUMN status TEXT NOT NULL DEFAULT 'in_progress'")


def ping(practitioner_id: str) -> bool:
    with _connect(practitioner_id) as conn:
        conn.execute("SELECT 1")
    return True


def create_client(
    practitioner_id: str, name: str, email: str, password_hash: str,
    dob: str | None = None, country: str | None = None, password_set: bool = True,
) -> dict:
    """password_set=False marks a practitioner-created invite: a real
    password hasn't been chosen by the client yet (the caller passes a
    throwaway hash nobody knows), and completing signup later is allowed to
    set a real one exactly once — see set_client_password's mark_set."""
    client = {"id": str(uuid.uuid4()), "name": name, "email": email,
              "password_hash": password_hash, "password_set": int(password_set),
              "dob": dob, "country": country, "created_at": _now()}
    with _connect(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO clients (id, name, email, password_hash, password_set,"
            " dob, country, created_at) VALUES (:id, :name, :email,"
            " :password_hash, :password_set, :dob, :country, :created_at)",
            client,
        )
    return client


def get_client(practitioner_id: str, client_id: str) -> dict | None:
    with _connect(practitioner_id) as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
        if row is None:
            return None
        entries = conn.execute(
            "SELECT * FROM record_entries WHERE client_id = ? "
            "ORDER BY created_at",
            (client_id,),
        ).fetchall()
    return {**dict(row), "entries": [dict(e) for e in entries]}


def set_client_password(
    practitioner_id: str, client_id: str, password_hash: str, mark_set: bool = False,
) -> None:
    """Set/replace a client's password.

    Used both when a Pro practitioner-created client (no password yet)
    completes their own signup (mark_set=True — flips password_set so this
    can't be done a second time by whoever merely knows the email), and for
    an ordinary already-authenticated password change (mark_set=False —
    leaves the flag as it already was).
    """
    with _connect(practitioner_id) as conn:
        if mark_set:
            conn.execute(
                "UPDATE clients SET password_hash = ?, password_set = 1 WHERE id = ?",
                (password_hash, client_id),
            )
        else:
            conn.execute(
                "UPDATE clients SET password_hash = ? WHERE id = ?",
                (password_hash, client_id),
            )


def get_client_by_email(practitioner_id: str, email: str) -> dict | None:
    with _connect(practitioner_id) as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE email = ?", (email,)
        ).fetchone()
    return dict(row) if row else None


def list_clients(practitioner_id: str) -> list[dict]:
    with _connect(practitioner_id) as conn:
        rows = conn.execute(
            """
            SELECT c.*,
                   (SELECT count(*) FROM sessions s WHERE s.client_id = c.id)
                       AS sessions,
                   (SELECT count(*) FROM record_entries e WHERE e.client_id = c.id)
                       AS entries
            FROM clients c ORDER BY c.created_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def delete_client(practitioner_id: str, client_id: str) -> bool:
    """Erase a client and their record.

    The audit rows are kept but their detail is redacted, so the trail still
    shows that a client existed and was erased without retaining the name — an
    erasure request should not also erase the evidence that it was honoured.
    """
    with _connect(practitioner_id) as conn:
        exists = conn.execute(
            "SELECT 1 FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
        if not exists:
            return False
        conn.execute(
            "DELETE FROM session_turns WHERE session_id IN "
            "(SELECT id FROM sessions WHERE client_id = ?)", (client_id,))
        conn.execute("DELETE FROM sessions WHERE client_id = ?", (client_id,))
        conn.execute("DELETE FROM record_entries WHERE client_id = ?", (client_id,))
        conn.execute(
            "DELETE FROM questionnaire_responses WHERE client_id = ?",
            (client_id,))
        conn.execute("DELETE FROM uploaded_files WHERE client_id = ?", (client_id,))
        conn.execute(
            "DELETE FROM wearable_data_points WHERE client_id = ?", (client_id,))
        conn.execute(
            "DELETE FROM wearable_connections WHERE client_id = ?", (client_id,))
        conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        conn.execute(
            "UPDATE audit_events SET detail = '[redacted on erasure]' "
            "WHERE client_id = ?",
            (client_id,),
        )
    log(practitioner_id, "practitioner", "client erased",
        "Client and record deleted; audit detail redacted", client_id)
    return True


def add_entry(practitioner_id: str, client_id: str, kind: str, content: str) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown entry kind: {kind}")
    entry = {"id": str(uuid.uuid4()), "client_id": client_id, "kind": kind,
              "content": content, "created_at": _now()}
    with _connect(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO record_entries (id, client_id, kind, content, created_at) "
            "VALUES (:id, :client_id, :kind, :content, :created_at)",
            entry,
        )
    return entry


# --- Consultation sessions ----------------------------------------------------

SESSION_STATUSES = ("in_progress", "done")


def create_session(practitioner_id: str, client_id: str, title: str) -> dict:
    row = {"id": str(uuid.uuid4()), "client_id": client_id,
           "title": title[:90], "started_at": _now(), "status": "in_progress"}
    with _connect(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO sessions (id, client_id, title, started_at, status) "
            "VALUES (:id, :client_id, :title, :started_at, :status)", row)
    return row


def set_session_status(practitioner_id: str, session_id: str, status: str) -> dict | None:
    if status not in SESSION_STATUSES:
        raise ValueError(f"unknown session status: {status}")
    with _connect(practitioner_id) as conn:
        exists = conn.execute(
            "SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not exists:
            return None
        conn.execute("UPDATE sessions SET status = ? WHERE id = ?", (status, session_id))
    return get_session(practitioner_id, session_id)


def add_turn(practitioner_id: str, session_id: str, question: str, answer: str,
             payload: dict) -> None:
    with _connect(practitioner_id) as conn:
        ordinal = conn.execute(
            "SELECT count(*) FROM session_turns WHERE session_id = ?",
            (session_id,)).fetchone()[0]
        conn.execute(
            "INSERT INTO session_turns (id, session_id, ordinal, question, answer,"
            " payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), session_id, ordinal, question, answer,
             json.dumps(payload), _now()),
        )


def list_recent_sessions(practitioner_id: str, limit: int = 8) -> list[dict]:
    """Most recent consultations across every client — the practitioner
    dashboard's historical-consultation widget, not scoped to one client."""
    with _connect(practitioner_id) as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.started_at, s.status, s.client_id,
                   c.name AS client_name,
                   (SELECT count(*) FROM session_turns t WHERE t.session_id = s.id)
                       AS turns
            FROM sessions s JOIN clients c ON c.id = s.client_id
            ORDER BY s.started_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_sessions(practitioner_id: str, client_id: str) -> list[dict]:
    with _connect(practitioner_id) as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.started_at, s.status,
                   (SELECT count(*) FROM session_turns t WHERE t.session_id = s.id)
                       AS turns
            FROM sessions s WHERE s.client_id = ?
            ORDER BY s.started_at DESC
            """,
            (client_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_session(practitioner_id: str, session_id: str) -> dict | None:
    with _connect(practitioner_id) as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?",
                           (session_id,)).fetchone()
        if row is None:
            return None
        turns = conn.execute(
            "SELECT question, answer, payload, created_at FROM session_turns "
            "WHERE session_id = ? ORDER BY ordinal", (session_id,)).fetchall()
    return {**dict(row), "turns": [
        {"question": t["question"], "answer": t["answer"],
         "created_at": t["created_at"], **json.loads(t["payload"])}
        for t in turns]}


def session_history(practitioner_id: str, session_id: str) -> list[dict]:
    """Prior turns, in the shape the Librarian and Specialist expect."""
    with _connect(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT question, answer FROM session_turns WHERE session_id = ? "
            "ORDER BY ordinal", (session_id,)).fetchall()
    return [dict(r) for r in rows]


def session_transcript(practitioner_id: str, session_id: str) -> str:
    turns = session_history(practitioner_id, session_id)
    return "\n\n".join(
        f"Question: {t['question']}\n\nAnswer:\n{t['answer']}" for t in turns)


def log(practitioner_id: str, actor: str, action: str, detail: str,
        client_id: str | None = None) -> None:
    """Record a client-touching event inside the vault."""
    with _connect(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO audit_events (id, ts, actor, action, detail, client_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), _now(), actor, action, detail, client_id),
        )


def audit(practitioner_id: str, limit: int = 100) -> list[dict]:
    with _connect(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT id, ts, actor, action, detail, client_id FROM audit_events "
            "ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{**dict(r), "vault": "client"} for r in rows]


def client_file_text(practitioner_id: str, client_id: str) -> str:
    """Flatten a client's record into the text the Specialist reads."""
    client = get_client(practitioner_id, client_id)
    if client is None:
        return ""
    lines = [
        f"Client: {client['name']}",
        f"Country: {client['country'] or 'not recorded'}",
        f"Date of birth: {client['dob'] or 'not recorded'}",
        "",
    ]
    if not client["entries"]:
        lines.append("(no labs, history or notes recorded yet)")
    for entry in client["entries"]:
        lines.append(f"[{entry['kind']} · {entry['created_at'][:10]}] {entry['content']}")
    return "\n".join(lines)


# --- Questionnaire responses ---------------------------------------------------

def save_questionnaire_response(
    practitioner_id: str, client_id: str, questionnaire_id: str,
    questionnaire_version: int, answers: dict,
) -> dict:
    row = {"id": str(uuid.uuid4()), "client_id": client_id,
           "questionnaire_id": questionnaire_id,
           "questionnaire_version": questionnaire_version,
           "answers_json": json.dumps(answers), "submitted_at": _now()}
    with _connect(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO questionnaire_responses (id, client_id, questionnaire_id,"
            " questionnaire_version, answers_json, submitted_at) VALUES"
            " (:id, :client_id, :questionnaire_id, :questionnaire_version,"
            " :answers_json, :submitted_at)",
            row,
        )
    return {**row, "answers": answers}


def get_questionnaire_response(practitioner_id: str, client_id: str) -> dict | None:
    with _connect(practitioner_id) as conn:
        row = conn.execute(
            "SELECT * FROM questionnaire_responses WHERE client_id = ? "
            "ORDER BY submitted_at DESC LIMIT 1",
            (client_id,),
        ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["answers"] = json.loads(data.pop("answers_json"))
    return data


# --- Uploaded files -------------------------------------------------------------

def save_uploaded_file(
    practitioner_id: str, client_id: str, original_name: str, media_type: str,
    storage_path: str,
) -> dict:
    row = {"id": str(uuid.uuid4()), "client_id": client_id,
           "original_name": original_name, "media_type": media_type,
           "storage_path": storage_path, "uploaded_at": _now()}
    with _connect(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO uploaded_files (id, client_id, original_name, "
            "media_type, storage_path, uploaded_at) VALUES (:id, :client_id, "
            ":original_name, :media_type, :storage_path, :uploaded_at)",
            row,
        )
    return row


def list_uploaded_files(practitioner_id: str, client_id: str) -> list[dict]:
    with _connect(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT * FROM uploaded_files WHERE client_id = ? "
            "ORDER BY uploaded_at DESC",
            (client_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# --- Wearables ------------------------------------------------------------------

def list_wearable_connections(practitioner_id: str, client_id: str) -> list[dict]:
    with _connect(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT provider, status, connected_at FROM wearable_connections "
            "WHERE client_id = ? ORDER BY connected_at", (client_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def create_wearable_connection(
    practitioner_id: str, client_id: str, provider: str,
) -> dict:
    if provider not in WEARABLE_PROVIDERS:
        raise ValueError(f"unknown wearable provider: {provider}")
    row = {"id": str(uuid.uuid4()), "client_id": client_id, "provider": provider,
           "status": "connected", "connected_at": _now()}
    with _connect(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO wearable_connections (id, client_id, provider, status,"
            " connected_at) VALUES (:id, :client_id, :provider, :status,"
            " :connected_at)",
            row,
        )
    return row


def seed_fixture_wearable_data(
    practitioner_id: str, client_id: str, provider: str,
) -> list[dict]:
    """Write fixture wearable_data_points for a newly connected provider.

    This is the v2 stand-in for a live vendor pull (specs/v2/06-client-portal.md)
    — not a real Oura/Whoop/Garmin API call.
    """
    if provider not in WEARABLE_PROVIDERS:
        raise ValueError(f"unknown wearable provider: {provider}")
    now = _now()
    points = [
        {"id": str(uuid.uuid4()), "client_id": client_id, "provider": provider,
         "metric": metric, "value": value, "recorded_at": now}
        for metric, value in FIXTURE_WEARABLE_METRICS[provider]
    ]
    with _connect(practitioner_id) as conn:
        conn.executemany(
            "INSERT INTO wearable_data_points (id, client_id, provider, metric,"
            " value, recorded_at) VALUES (:id, :client_id, :provider, :metric,"
            " :value, :recorded_at)",
            points,
        )
    return points


def list_wearable_data(practitioner_id: str, client_id: str) -> list[dict]:
    with _connect(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT * FROM wearable_data_points WHERE client_id = ? "
            "ORDER BY recorded_at DESC",
            (client_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# --- Session documents (clinician note / client report) -----------------------

DOCUMENT_KINDS = ("clinician_note", "client_report")
DOCUMENT_STATUSES = ("draft", "final")


def save_document(
    practitioner_id: str, session_id: str, client_id: str, kind: str,
    content: str, status: str = "draft",
) -> dict:
    if kind not in DOCUMENT_KINDS:
        raise ValueError(f"unknown document kind: {kind}")
    if status not in DOCUMENT_STATUSES:
        raise ValueError(f"unknown document status: {status}")
    row = {"id": str(uuid.uuid4()), "session_id": session_id, "client_id": client_id,
           "kind": kind, "status": status, "content": content, "updated_at": _now()}
    with _connect(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO session_documents (id, session_id, client_id, kind, "
            "status, content, updated_at) VALUES (:id, :session_id, :client_id, "
            ":kind, :status, :content, :updated_at) "
            "ON CONFLICT(session_id, kind) DO UPDATE SET "
            "status = excluded.status, content = excluded.content, "
            "updated_at = excluded.updated_at",
            row,
        )
    return get_document(practitioner_id, session_id, kind)


def get_document(practitioner_id: str, session_id: str, kind: str) -> dict | None:
    with _connect(practitioner_id) as conn:
        row = conn.execute(
            "SELECT * FROM session_documents WHERE session_id = ? AND kind = ?",
            (session_id, kind),
        ).fetchone()
    return dict(row) if row else None


def list_documents(practitioner_id: str, client_id: str) -> list[dict]:
    """All documents across a client's sessions, newest first — the
    reports & documents side panel."""
    with _connect(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT d.*, s.title AS session_title FROM session_documents d "
            "JOIN sessions s ON s.id = d.session_id "
            "WHERE d.client_id = ? ORDER BY d.updated_at DESC",
            (client_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# --- Intake notes (clinician notes per questionnaire theme) --------------------

def upsert_intake_note(practitioner_id: str, client_id: str, theme: str, note: str) -> dict:
    row = {"client_id": client_id, "theme": theme, "note": note, "updated_at": _now()}
    with _connect(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO intake_notes (client_id, theme, note, updated_at) "
            "VALUES (:client_id, :theme, :note, :updated_at) "
            "ON CONFLICT(client_id, theme) DO UPDATE SET "
            "note = excluded.note, updated_at = excluded.updated_at",
            row,
        )
    return row


def list_intake_notes(practitioner_id: str, client_id: str) -> dict:
    """Returns {theme: note} for a client."""
    with _connect(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT theme, note FROM intake_notes WHERE client_id = ?",
            (client_id,),
        ).fetchall()
    return {r["theme"]: r["note"] for r in rows}


# --- Source weights (practitioner's own view of the shared library) -----------

def get_source_weights(practitioner_id: str) -> dict:
    """Returns {source_id: weight} — this practitioner's own overrides only."""
    with _connect(practitioner_id) as conn:
        rows = conn.execute("SELECT source_id, weight FROM source_weights").fetchall()
    return {r["source_id"]: r["weight"] for r in rows}


def set_source_weight(practitioner_id: str, source_id: str, weight: int) -> dict:
    if not 1 <= weight <= 10:
        raise ValueError("weight must be between 1 and 10")
    row = {"source_id": source_id, "weight": weight, "updated_at": _now()}
    with _connect(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO source_weights (source_id, weight, updated_at) "
            "VALUES (:source_id, :weight, :updated_at) "
            "ON CONFLICT(source_id) DO UPDATE SET "
            "weight = excluded.weight, updated_at = excluded.updated_at",
            row,
        )
    return row
