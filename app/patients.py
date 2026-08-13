"""The patient vault: SQLite, deliberately separate from the knowledge library.

Patient records are small at PoC scale, so a consultation passes the whole file
to the Specialist rather than retrieving over it.
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    path = Path(cfg.sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                country TEXT NOT NULL,
                dob TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS record_entries (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL REFERENCES patients(id),
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS entries_by_patient
                ON record_entries(patient_id, created_at);
            -- Audit of anything that touches a patient. Kept here rather than in
            -- the knowledge library because these rows carry clinical detail (the
            -- question asked, which patient it was about), and that must not leave
            -- the vault.
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                ts TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT NOT NULL,
                patient_id TEXT
            );
            CREATE INDEX IF NOT EXISTS audit_by_ts ON audit_events(ts);
            -- A consultation is a conversation, not a single question. Sessions
            -- and their turns live in the vault: the questions asked and answers
            -- given are clinical detail about this patient.
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                title TEXT NOT NULL,
                started_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sessions_by_patient
                ON sessions(patient_id, started_at);
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
            """
        )


def ping() -> bool:
    with _connect() as conn:
        conn.execute("SELECT 1")
    return True


def create_patient(name: str, country: str, dob: str | None) -> dict:
    patient = {"id": str(uuid.uuid4()), "name": name, "country": country,
               "dob": dob, "created_at": _now()}
    with _connect() as conn:
        conn.execute(
            "INSERT INTO patients (id, name, country, dob, created_at) "
            "VALUES (:id, :name, :country, :dob, :created_at)",
            patient,
        )
    return patient


def list_patients(search: str = "", country: str = "") -> list[dict]:
    """Patients, optionally filtered by a name substring and/or country."""
    where, params = [], []
    if search.strip():
        where.append("lower(name) LIKE ?")
        params.append(f"%{search.strip().lower()}%")
    if country.strip():
        where.append("country = ?")
        params.append(country.strip())
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT p.*,
                   (SELECT count(*) FROM sessions s WHERE s.patient_id = p.id)
                       AS sessions,
                   (SELECT count(*) FROM record_entries e WHERE e.patient_id = p.id)
                       AS entries
            FROM patients p {clause} ORDER BY p.created_at DESC
            """,
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def get_patient(patient_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        if row is None:
            return None
        entries = conn.execute(
            "SELECT * FROM record_entries WHERE patient_id = ? "
            "ORDER BY created_at",
            (patient_id,),
        ).fetchall()
    return {**dict(row), "entries": [dict(e) for e in entries]}


def add_entry(patient_id: str, kind: str, content: str) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown entry kind: {kind}")
    entry = {"id": str(uuid.uuid4()), "patient_id": patient_id, "kind": kind,
             "content": content, "created_at": _now()}
    with _connect() as conn:
        conn.execute(
            "INSERT INTO record_entries (id, patient_id, kind, content, created_at) "
            "VALUES (:id, :patient_id, :kind, :content, :created_at)",
            entry,
        )
    return entry


def delete_patient(patient_id: str) -> bool:
    """Erase a patient and their record.

    The audit rows are kept but their detail is redacted, so the trail still shows
    that a patient existed and was erased without retaining the name — an erasure
    request should not also erase the evidence that it was honoured.
    """
    with _connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        if not exists:
            return False
        conn.execute(
            "DELETE FROM session_turns WHERE session_id IN "
            "(SELECT id FROM sessions WHERE patient_id = ?)", (patient_id,))
        conn.execute("DELETE FROM sessions WHERE patient_id = ?", (patient_id,))
        conn.execute("DELETE FROM record_entries WHERE patient_id = ?", (patient_id,))
        conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.execute(
            "UPDATE audit_events SET detail = '[redacted on erasure]' "
            "WHERE patient_id = ?",
            (patient_id,),
        )
    log("practitioner", "patient erased",
        "Patient and record deleted; audit detail redacted", patient_id)
    return True


# --- Consultation sessions ----------------------------------------------------

def create_session(patient_id: str, title: str) -> dict:
    row = {"id": str(uuid.uuid4()), "patient_id": patient_id,
           "title": title[:90], "started_at": _now()}
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (id, patient_id, title, started_at) "
            "VALUES (:id, :patient_id, :title, :started_at)", row)
    return row


def add_turn(session_id: str, question: str, answer: str, payload: dict) -> None:
    with _connect() as conn:
        ordinal = conn.execute(
            "SELECT count(*) FROM session_turns WHERE session_id = ?",
            (session_id,)).fetchone()[0]
        conn.execute(
            "INSERT INTO session_turns (id, session_id, ordinal, question, answer,"
            " payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), session_id, ordinal, question, answer,
             json.dumps(payload), _now()),
        )


def list_sessions(patient_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.started_at,
                   (SELECT count(*) FROM session_turns t WHERE t.session_id = s.id)
                       AS turns
            FROM sessions s WHERE s.patient_id = ?
            ORDER BY s.started_at DESC
            """,
            (patient_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_session(session_id: str) -> dict | None:
    with _connect() as conn:
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


def session_history(session_id: str) -> list[dict]:
    """Prior turns, in the shape the Librarian and Specialist expect."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT question, answer FROM session_turns WHERE session_id = ? "
            "ORDER BY ordinal", (session_id,)).fetchall()
    return [dict(r) for r in rows]


def session_transcript(session_id: str) -> str:
    turns = session_history(session_id)
    return "\n\n".join(
        f"Question: {t['question']}\n\nAnswer:\n{t['answer']}" for t in turns)


def log(actor: str, action: str, detail: str, patient_id: str | None = None) -> None:
    """Record a patient-touching event inside the vault."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO audit_events (id, ts, actor, action, detail, patient_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), _now(), actor, action, detail, patient_id),
        )


def audit(limit: int = 100) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, ts, actor, action, detail, patient_id FROM audit_events "
            "ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{**dict(r), "vault": "patient"} for r in rows]


def patient_file_text(patient_id: str) -> str:
    """Flatten a patient's record into the text the Specialist reads."""
    patient = get_patient(patient_id)
    if patient is None:
        return ""
    lines = [
        f"Patient: {patient['name']}",
        f"Country: {patient['country']}",
        f"Date of birth: {patient['dob'] or 'not recorded'}",
        "",
    ]
    if not patient["entries"]:
        lines.append("(no labs, history or notes recorded yet)")
    for entry in patient["entries"]:
        lines.append(f"[{entry['kind']} · {entry['created_at'][:10]}] {entry['content']}")
    return "\n".join(lines)
