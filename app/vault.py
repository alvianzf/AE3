"""The client vault: one Postgres schema per Pro practitioner.

specs/v6 — used to be one SQLite file per practitioner
(cfg.vaults_path/<id>.db); now one Postgres schema (vault_<id>) inside
the same shared database as the core store, via app/db.py's
vault_connection() (SET search_path scopes every query in this module to
that one practitioner's tables, same isolation guarantee the separate
file used to give). Every function signature and return shape is
unchanged, so nothing outside this module needed to change.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import get_config
from .db import schema_connection, vault_connection, vault_connection_creating_schema

cfg = get_config()

KINDS = ("lab", "history", "note", "session_summary", "condition", "medication",
         "protocol", "document")
# "protocol" added: client-specific clinical protocols staged and implemented
# at the practitioner's sole discretion (what interventions and when).
# "condition"/"medication" added for app/patient/context.py — structured
# retrieval-time patient context needs to tell an active condition from a
# current medication, which the older "history"/"note" kinds never
# distinguished. Existing entries stay "history"/"note"; get_patient_context()
# has a documented heuristic fallback for them rather than requiring a
# backfill migration before it can be used.
# "document" added for the Record redesign (specs/v9): every uploaded file
# gets one of these automatically at upload time (app/main.py's
# _save_uploaded_file), not just lab-classified ones — it's upload-only,
# never offered in the Record tab's manual "add entry" form.

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# Factored out of ensure_schema() so ensure_schema_by_name() (boot-time
# repair of a schema whose owning practitioner_id can't be recovered —
# see app/db.py's list_vault_schemas()) runs the identical DDL rather
# than a second copy that could drift out of sync with this one.
_SCHEMA_DDL = """
            CREATE TABLE IF NOT EXISTS clients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                password_set BOOLEAN NOT NULL DEFAULT TRUE,
                dob TEXT,
                country TEXT,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TEXT NOT NULL
            );
            -- CREATE TABLE IF NOT EXISTS above is a no-op for a vault schema
            -- that already existed before `active` was added, same gap this
            -- module's own docstring already calls out for password_set —
            -- so apply it explicitly for every vault, new or old.
            ALTER TABLE clients ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;
            -- specs/v7/06 — same onboarding-tour flag as admins/
            -- practitioners (app/core_store.py), applied here too since a
            -- client's own account lives in this per-practitioner vault
            -- schema, not core_store.
            ALTER TABLE clients ADD COLUMN IF NOT EXISTS tour_completed BOOLEAN NOT NULL DEFAULT FALSE;
            CREATE TABLE IF NOT EXISTS record_entries (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL REFERENCES clients(id),
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                session_id TEXT
            );
            CREATE INDEX IF NOT EXISTS entries_by_client
                ON record_entries(client_id, created_at);
            -- specs/v9/03 — a living, bi-temporal view of a client's lab
            -- markers, so a consult's opening briefing can read an
            -- already-current trend ("ferritin falling for 4 tests")
            -- instead of an LLM re-deriving it from raw record_entries on
            -- every single consult. Disposable/rebuildable by design, never
            -- the sole source of truth: record_entries stays authoritative,
            -- and scripts/reconcile_clinical_state.py recomputes this table
            -- from scratch to catch any drift. v1 scope is lab markers only
            -- (app/reasoning/clinical_state.py) — condition/medication/
            -- protocol entries are already atomic and don't need this.
            CREATE TABLE IF NOT EXISTS client_clinical_state (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL REFERENCES clients(id),
                label TEXT NOT NULL,
                display_label TEXT NOT NULL,
                value TEXT,
                unit TEXT,
                reference_range TEXT,
                flag TEXT,
                trend TEXT,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                source_entry_id TEXT NOT NULL REFERENCES record_entries(id),
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS clinical_state_current
                ON client_clinical_state(client_id, label) WHERE valid_to IS NULL;
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
                status TEXT NOT NULL DEFAULT 'in_progress',
                initial_summary TEXT
            );
            ALTER TABLE sessions ADD COLUMN IF NOT EXISTS initial_summary TEXT;
            CREATE INDEX IF NOT EXISTS sessions_by_client
                ON sessions(client_id, started_at);
            -- list_recent_sessions() orders by started_at across every
            -- client with no WHERE clause (the dashboard's cross-client
            -- recent-consultations widget) — the (client_id, started_at)
            -- index above can't back that scan since it isn't filtered by
            -- client_id, so this needs its own index on started_at alone.
            CREATE INDEX IF NOT EXISTS sessions_by_started_at
                ON sessions(started_at);
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
            -- Tidying a document's HTML for PDF export (app/pdf_tidy.py)
            -- is a real Claude call, not something to repeat on every
            -- download/preview — cached here, keyed by a hash of the
            -- `content` it was generated from, so the next PDF request
            -- only re-tidies once that content actually changes.
            ALTER TABLE session_documents ADD COLUMN IF NOT EXISTS pdf_html TEXT;
            ALTER TABLE session_documents ADD COLUMN IF NOT EXISTS pdf_source_hash TEXT;
            -- An image pasted, dropped, or cropped into a session document —
            -- its own table, not a column on session_documents, since one
            -- document can hold several and a document's content only needs
            -- to reference them by id (Consult Draft Editor).
            CREATE TABLE IF NOT EXISTS session_assets (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                client_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS assets_by_session
                ON session_assets(session_id);
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
                created_at TEXT NOT NULL,
                UNIQUE (session_id, ordinal)
            );
            CREATE TABLE IF NOT EXISTS questionnaire_responses (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                questionnaire_id TEXT NOT NULL,
                questionnaire_version INTEGER NOT NULL,
                answers_json TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                viewed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS responses_by_client
                ON questionnaire_responses(client_id, submitted_at);
            -- Client Intake Links — the actual link state (draft answers,
            -- one-way submitted flip) lives here in the vault, since it's
            -- clinical-adjacent data; app/core_store.py's
            -- intake_link_directory is only the token -> practitioner_id
            -- routing pointer that finds this row in the first place.
            -- client_id is NULL for an 'initial'-kind link until submission
            -- creates the client (see _owned_session's sibling check for
            -- intake links, app/main.py).
            CREATE TABLE IF NOT EXISTS intake_links (
                token TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                questionnaire_id TEXT,
                questionnaire_version INTEGER,
                client_id TEXT,
                draft_answers_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                submitted_at TEXT
            );
            CREATE INDEX IF NOT EXISTS intake_links_by_client
                ON intake_links(client_id, created_at);
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
            -- An uploaded file used to be a pure attachment — Consult never
            -- read it (found live: uploading a client's real lab PDF, then
            -- asking Consult to prepare for the visit, got "no labs on
            -- file"). Extracted once at upload time (same PDF/OCR/.docx
            -- pipeline the library uses, app/main.py's _extract_pages) and
            -- read from here by app/patient/context.py, not re-extracted
            -- per consult call.
            ALTER TABLE uploaded_files ADD COLUMN IF NOT EXISTS extracted_text TEXT;
            ALTER TABLE uploaded_files ADD COLUMN IF NOT EXISTS
                extraction_status TEXT NOT NULL DEFAULT 'pending';
            -- Which part of the client's record this file's content
            -- actually belongs to — set once, at upload time, from the
            -- same extracted text (app/main.py's _categorize_upload), so
            -- an uploaded file surfaces where a practitioner would
            -- actually go looking for it (Record for a lab/test result)
            -- instead of only ever sitting in one undifferentiated pile.
            ALTER TABLE uploaded_files ADD COLUMN IF NOT EXISTS
                category TEXT NOT NULL DEFAULT 'document';
            -- AI document understanding (specs/v9 Record redesign): every
            -- uploaded file is classified in the background after extraction
            -- (app/reasoning/document_insights.py), independent of the
            -- synchronous `category` heuristic above, which keeps deciding
            -- the immediate lab-vs-document split and the lab auto-entry
            -- behavior unchanged. NULL ai_doc_type means "not yet classified
            -- (pending or failed)" — the Record tab must render that as a
            -- processing/unavailable state, never assume it's always set.
            ALTER TABLE uploaded_files ADD COLUMN IF NOT EXISTS ai_doc_type TEXT;
            ALTER TABLE uploaded_files ADD COLUMN IF NOT EXISTS ai_summary TEXT;
            ALTER TABLE uploaded_files ADD COLUMN IF NOT EXISTS ai_highlights_json TEXT;
            ALTER TABLE uploaded_files ADD COLUMN IF NOT EXISTS ai_classified_at TEXT;
            -- The record_entries row this upload is represented by in the
            -- unified Record timeline (every upload gets one now, not just
            -- lab-classified ones — see KINDS' "document" entry below).
            ALTER TABLE uploaded_files ADD COLUMN IF NOT EXISTS record_entry_id TEXT;
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
                value DOUBLE PRECISION NOT NULL,
                recorded_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS data_points_by_client
                ON wearable_data_points(client_id, recorded_at);
            """


def _vector_schema_ddl() -> str:
    """Separate from _SCHEMA_DDL (a plain string, not an f-string) since
    this needs cfg.embedding_dimensions interpolated — same reasoning
    app/retrieval/pgvector_store.py's own ensure_schema() gives. Chunks +
    embeds each uploaded client file (app/main.py's _save_uploaded_file)
    so Consult can retrieve only the passages relevant to the current
    question (app/patient/context.py's get_relevant_uploaded_excerpts)
    instead of concatenating every uploaded document's full text into
    every prompt — found live: that doesn't scale past a client with a
    couple of files, let alone a long-term client with years of lab
    panels and prior consult documents attached."""
    return f"""
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE IF NOT EXISTS client_document_chunks (
            id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            file_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding vector({cfg.embedding_dimensions}) NOT NULL
        );
        CREATE INDEX IF NOT EXISTS client_document_chunks_by_client
            ON client_document_chunks(client_id);
        """


def ensure_schema(practitioner_id: str) -> None:
    with vault_connection_creating_schema(practitioner_id) as conn:
        conn.executescript(_SCHEMA_DDL)
        conn.executescript(_vector_schema_ddl())


def ensure_schema_by_name(schema_name: str) -> None:
    """Same DDL as ensure_schema(), against an already-known Postgres
    schema name directly — used to repair every vault_* schema that
    actually exists (app/main.py's boot-time loop), including one whose
    owning practitioner_id can't be reconstructed from the schema name
    (vault_schema_name()'s sanitization is one-way) or whose
    practitioners row is missing/stale in the core store."""
    with schema_connection(schema_name) as conn:
        conn.executescript(_SCHEMA_DDL)
        conn.executescript(_vector_schema_ddl())


def ping(practitioner_id: str) -> bool:
    with vault_connection(practitioner_id) as conn:
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
              "password_hash": password_hash, "password_set": password_set,
              "dob": dob, "country": country, "created_at": _now()}
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO clients (id, name, email, password_hash, password_set,"
            " dob, country, created_at) VALUES (%(id)s, %(name)s, %(email)s,"
            " %(password_hash)s, %(password_set)s, %(dob)s, %(country)s, %(created_at)s)",
            client,
        )
    return client


def get_client(practitioner_id: str, client_id: str) -> dict | None:
    with vault_connection(practitioner_id) as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE id = %s", (client_id,)
        ).fetchone()
        if row is None:
            return None
        entries = conn.execute(
            "SELECT * FROM record_entries WHERE client_id = %s "
            "ORDER BY created_at",
            (client_id,),
        ).fetchall()
    return {**dict(row), "entries": [dict(e) for e in entries]}


def get_client_by_email(practitioner_id: str, email: str) -> dict | None:
    with vault_connection(practitioner_id) as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE email = %s", (email,)
        ).fetchone()
    return dict(row) if row else None


def list_clients(practitioner_id: str) -> list[dict]:
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            """
            SELECT c.*,
                   (SELECT count(*) FROM sessions s WHERE s.client_id = c.id)
                       AS sessions,
                   (SELECT max(s.started_at) FROM sessions s WHERE s.client_id = c.id)
                       AS last_session_at,
                   (SELECT count(*) FROM record_entries e WHERE e.client_id = c.id)
                       AS entries,
                   EXISTS (
                       SELECT 1 FROM questionnaire_responses qr
                       WHERE qr.client_id = c.id AND qr.viewed_at IS NULL
                         AND qr.submitted_at = (
                             SELECT max(qr2.submitted_at) FROM questionnaire_responses qr2
                             WHERE qr2.client_id = qr.client_id)
                   ) AS has_unviewed_intake
            FROM clients c ORDER BY c.created_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def set_client_active(practitioner_id: str, client_id: str, active: bool) -> dict | None:
    with vault_connection(practitioner_id) as conn:
        exists = conn.execute(
            "SELECT 1 FROM clients WHERE id = %s", (client_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE clients SET active = %s WHERE id = %s", (active, client_id)
        )
        row = conn.execute("SELECT * FROM clients WHERE id = %s", (client_id,)).fetchone()
    return dict(row)


def delete_client(practitioner_id: str, client_id: str) -> bool:
    """Erase a client and their record.

    The audit rows are kept but their detail is redacted, so the trail still
    shows that a client existed and was erased without retaining the name — an
    erasure request should not also erase the evidence that it was honoured.
    """
    with vault_connection(practitioner_id) as conn:
        exists = conn.execute(
            "SELECT 1 FROM clients WHERE id = %s", (client_id,)
        ).fetchone()
        if not exists:
            return False
        conn.execute(
            "DELETE FROM session_turns WHERE session_id IN "
            "(SELECT id FROM sessions WHERE client_id = %s)", (client_id,))
        conn.execute("DELETE FROM sessions WHERE client_id = %s", (client_id,))
        # Must precede record_entries below — client_clinical_state.
        # source_entry_id references record_entries(id) with no cascade,
        # so deleting record_entries first throws a ForeignKeyViolation
        # (found live, 2026-11-25, in this feature's own first end-to-end
        # test: erasing a client with any tracked lab-marker trend failed
        # outright).
        conn.execute("DELETE FROM client_clinical_state WHERE client_id = %s", (client_id,))
        conn.execute("DELETE FROM record_entries WHERE client_id = %s", (client_id,))
        conn.execute(
            "DELETE FROM questionnaire_responses WHERE client_id = %s",
            (client_id,))
        # Delete the file bytes too, not just the row — an "erased" client's
        # actual files must not survive on disk indefinitely.
        file_rows = conn.execute(
            "SELECT storage_path FROM uploaded_files WHERE client_id = %s",
            (client_id,)).fetchall()
        for row in file_rows:
            try:
                Path(row["storage_path"]).unlink(missing_ok=True)
            except OSError as exc:
                logging.warning("could not remove uploaded file %s: %s",
                                row["storage_path"], exc)
        conn.execute("DELETE FROM uploaded_files WHERE client_id = %s", (client_id,))
        conn.execute(
            "DELETE FROM client_document_chunks WHERE client_id = %s", (client_id,))
        conn.execute(
            "DELETE FROM wearable_data_points WHERE client_id = %s", (client_id,))
        conn.execute(
            "DELETE FROM wearable_connections WHERE client_id = %s", (client_id,))
        conn.execute("DELETE FROM clients WHERE id = %s", (client_id,))
        conn.execute(
            "UPDATE audit_events SET detail = '[redacted on erasure]' "
            "WHERE client_id = %s",
            (client_id,),
        )
    log(practitioner_id, "practitioner", "client erased",
        "Client and record deleted; audit detail redacted", client_id)
    return True


def add_entry(practitioner_id: str, client_id: str, kind: str, content: str,
              session_id: str | None = None) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown entry kind: {kind}")
    entry = {"id": str(uuid.uuid4()), "client_id": client_id, "kind": kind,
              "content": content, "created_at": _now(), "session_id": session_id}
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO record_entries (id, client_id, kind, content, created_at, session_id) "
            "VALUES (%(id)s, %(client_id)s, %(kind)s, %(content)s, %(created_at)s, %(session_id)s)",
            entry,
        )
    return entry


_CLINICAL_STATE_COLUMNS = (
    "id, client_id, label, display_label, value, unit, reference_range, "
    "flag, trend, valid_from, valid_to, source_entry_id, created_at"
)


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


# A tolerance, not an exact-equality check — two draws of the same
# genuinely stable marker rarely land on the identical float, and
# reporting "falling" on noise would be worse than useless on a trend a
# practitioner is expected to act on. 2% of the prior value, floor 0.01,
# hardcoded per CLAUDE.md's "hardcode until there's a real reason to
# configure it" — a single call site, no product request for a different
# threshold yet.
_TREND_TOLERANCE_FRACTION = 0.02


def _compute_trend(old_value: str | None, new_value: str | None) -> str | None:
    old_f, new_f = _parse_float(old_value), _parse_float(new_value)
    if old_f is None or new_f is None:
        return None
    tolerance = max(abs(old_f) * _TREND_TOLERANCE_FRACTION, 0.01)
    if new_f > old_f + tolerance:
        return "rising"
    if new_f < old_f - tolerance:
        return "falling"
    return "stable"


def upsert_clinical_state_marker(
    practitioner_id: str, client_id: str, *, label: str, value: str | None = None,
    unit: str | None = None, reference_range: str | None = None,
    flag: str | None = None, source_entry_id: str,
) -> dict:
    """One lab marker's current-value row, bi-temporally versioned —
    specs/v9/03. `label` is canon()-normalized (app/graph/store.py — reused
    rather than reinvented, it already resolves exactly this clinical-
    term-aliasing problem, e.g. "serum ferritin" -> "ferritin") so the same
    marker reported under slightly different wording across lab reports
    still tracks as one trend, not two unrelated ones.

    Deterministic — no LLM call in this function. The caller
    (app/reasoning/clinical_state.py's update_lab_state, run in the
    background after a lab entry is saved) already did the one LLM call
    this marker needed, to extract it from free text in the first place."""
    from .graph.store import canon
    normalized = canon(label)
    now = _now()
    with vault_connection(practitioner_id) as conn:
        current = conn.execute(
            f"SELECT {_CLINICAL_STATE_COLUMNS} FROM client_clinical_state "
            "WHERE client_id = %s AND label = %s AND valid_to IS NULL",
            (client_id, normalized),
        ).fetchone()
        trend = _compute_trend(current["value"] if current else None, value)
        if current:
            conn.execute(
                "UPDATE client_clinical_state SET valid_to = %s WHERE id = %s",
                (now, current["id"]),
            )
        row = {
            "id": str(uuid.uuid4()), "client_id": client_id, "label": normalized,
            "display_label": label, "value": value, "unit": unit,
            "reference_range": reference_range, "flag": flag, "trend": trend,
            "valid_from": now, "valid_to": None, "source_entry_id": source_entry_id,
            "created_at": now,
        }
        conn.execute(
            f"INSERT INTO client_clinical_state ({_CLINICAL_STATE_COLUMNS}) "
            f"VALUES (%(id)s, %(client_id)s, %(label)s, %(display_label)s, %(value)s, "
            f"%(unit)s, %(reference_range)s, %(flag)s, %(trend)s, %(valid_from)s, "
            f"%(valid_to)s, %(source_entry_id)s, %(created_at)s)",
            row,
        )
    return row


def get_clinical_state(practitioner_id: str, client_id: str) -> list[dict]:
    """A client's current lab-marker trends — the "living state" read side.
    Never the only place this data lives: record_entries (the raw lab
    text) remains authoritative; this is a disposable, rebuildable
    projection of it (scripts/reconcile_clinical_state.py rebuilds and
    diffs it from scratch for exactly this reason)."""
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            f"SELECT {_CLINICAL_STATE_COLUMNS} FROM client_clinical_state "
            "WHERE client_id = %s AND valid_to IS NULL ORDER BY display_label",
            (client_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def clinical_state_as_of(practitioner_id: str, client_id: str, cutoff: str) -> list[dict]:
    """Same as get_clinical_state(), but strictly as of a point in time —
    the same "nothing after consultation_point" contract
    get_patient_history_up_to() already honors for every other query, so
    a past session's reconstructed briefing stays reproducible rather
    than silently picking up a marker recorded after that consult."""
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            f"SELECT {_CLINICAL_STATE_COLUMNS} FROM client_clinical_state "
            "WHERE client_id = %s AND valid_from <= %s "
            "AND (valid_to IS NULL OR valid_to > %s) ORDER BY display_label",
            (client_id, cutoff, cutoff),
        ).fetchall()
    return [dict(r) for r in rows]


def list_entries(practitioner_id: str, client_id: str) -> list[dict]:
    """A client's clinical record entries — conditions, medications, labs,
    and the older history/note kinds — for the practitioner-facing record
    panel. Excludes session_summary, the same exclusion
    app/patient/context.py's get_patient_context() already makes: a past
    AI answer is consult history, not patient baseline data."""
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT * FROM record_entries WHERE client_id = %s AND kind != 'session_summary' "
            "ORDER BY created_at DESC",
            (client_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_entry(practitioner_id: str, client_id: str, entry_id: str) -> bool:
    with vault_connection(practitioner_id) as conn:
        entry = conn.execute(
            "SELECT kind FROM record_entries WHERE id = %s AND client_id = %s",
            (entry_id, client_id),
        ).fetchone()
        if not entry:
            return False
        # Same reasoning as delete_client()'s own fix: client_clinical_
        # state.source_entry_id references this row with no cascade.
        # Deleting its derived marker rows along with it is also the
        # honest behavior, not just an FK workaround — a marker whose
        # only source entry was removed shouldn't keep being shown as
        # "current" with nothing left to trace it back to.
        conn.execute("DELETE FROM client_clinical_state WHERE source_entry_id = %s", (entry_id,))
        # A "document" entry IS the uploaded file, as far as the Record tab
        # is concerned — deleting it from Record should delete the file
        # (bytes, chunks, row) too, not leave an orphaned upload that no
        # longer shows up anywhere but is still downloadable/retrievable.
        if entry["kind"] == "document":
            file_row = conn.execute(
                "SELECT id, storage_path FROM uploaded_files WHERE record_entry_id = %s",
                (entry_id,),
            ).fetchone()
            if file_row:
                try:
                    Path(file_row["storage_path"]).unlink(missing_ok=True)
                except OSError as exc:
                    logging.warning("could not remove uploaded file %s: %s",
                                    file_row["storage_path"], exc)
                conn.execute("DELETE FROM client_document_chunks WHERE file_id = %s", (file_row["id"],))
                conn.execute("DELETE FROM uploaded_files WHERE id = %s", (file_row["id"],))
        conn.execute("DELETE FROM record_entries WHERE id = %s", (entry_id,))
    return True


# --- Consultation sessions ----------------------------------------------------

SESSION_STATUSES = ("in_progress", "done")


def create_session(
    practitioner_id: str,
    client_id: str,
    title: str,
    initial_summary: str | None = None,
    started_at: str | None = None,
) -> dict:
    row = {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "title": title[:90],
        "started_at": started_at or _now(),
        "status": "in_progress",
        "initial_summary": initial_summary,
    }
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO sessions (id, client_id, title, started_at, status, initial_summary) "
            "VALUES (%(id)s, %(client_id)s, %(title)s, %(started_at)s, %(status)s, %(initial_summary)s)",
            row,
        )
    return row


def update_session_title(practitioner_id: str, session_id: str, title: str) -> None:
    with vault_connection(practitioner_id) as conn:
        conn.execute("UPDATE sessions SET title = %s WHERE id = %s", (title[:90], session_id))


def update_session_initial_summary(practitioner_id: str, session_id: str, initial_summary: str) -> None:
    with vault_connection(practitioner_id) as conn:
        conn.execute("UPDATE sessions SET initial_summary = %s WHERE id = %s", (initial_summary, session_id))


def set_session_status(practitioner_id: str, session_id: str, status: str) -> dict | None:
    if status not in SESSION_STATUSES:
        raise ValueError(f"unknown session status: {status}")
    with vault_connection(practitioner_id) as conn:
        exists = conn.execute(
            "SELECT 1 FROM sessions WHERE id = %s", (session_id,)).fetchone()
        if not exists:
            return None
        conn.execute("UPDATE sessions SET status = %s WHERE id = %s", (status, session_id))
    return get_session(practitioner_id, session_id)


def add_turn(practitioner_id: str, session_id: str, question: str, answer: str,
             payload: dict) -> None:
    # `SELECT ... FOR UPDATE` on the session row serializes concurrent
    # add_turn() calls for the same session (two browser tabs, a retried
    # request after a timeout) so two callers can't both compute the same
    # next ordinal — the old SQLite-per-vault-file design had this for
    # free via the file's single-writer lock; a shared, pooled Postgres
    # connection doesn't, so it has to be explicit here. The UNIQUE
    # (session_id, ordinal) constraint (ensure_schema above) is the
    # backstop: if this lock is ever bypassed, the insert fails loudly
    # instead of silently writing two turns with the same ordinal.
    with vault_connection(practitioner_id) as conn:
        conn.execute("SELECT id FROM sessions WHERE id = %s FOR UPDATE", (session_id,))
        ordinal = conn.execute(
            "SELECT count(*) AS n FROM session_turns WHERE session_id = %s",
            (session_id,)).fetchone()["n"]
        conn.execute(
            "INSERT INTO session_turns (id, session_id, ordinal, question, answer,"
            " payload, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), session_id, ordinal, question, answer,
             json.dumps(payload), _now()),
        )


def list_recent_sessions(practitioner_id: str, limit: int = 8) -> list[dict]:
    """Most recent consultations across every client — the practitioner
    dashboard's historical-consultation widget, not scoped to one client."""
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.started_at, s.status, s.client_id,
                   c.name AS client_name,
                   (SELECT count(*) FROM session_turns t WHERE t.session_id = s.id)
                       AS turns,
                   (SELECT t.question FROM session_turns t WHERE t.session_id = s.id
                       ORDER BY t.ordinal DESC LIMIT 1) AS last_question
            FROM sessions s JOIN clients c ON c.id = s.client_id
            ORDER BY s.started_at DESC LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_sessions(practitioner_id: str, client_id: str) -> list[dict]:
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.started_at, s.status, s.initial_summary,
                   (SELECT count(*) FROM session_turns t WHERE t.session_id = s.id)
                       AS turns,
                   (SELECT t.question FROM session_turns t WHERE t.session_id = s.id
                       ORDER BY t.ordinal DESC LIMIT 1) AS last_question,
                   (SELECT e.content FROM record_entries e
                       WHERE e.session_id = s.id AND e.kind = 'session_summary'
                       ORDER BY e.created_at DESC LIMIT 1) AS summary
            FROM sessions s WHERE s.client_id = %s
            ORDER BY s.started_at DESC
            """,
            (client_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_patient_history_up_to(practitioner_id: str, client_id: str, consultation_point: str) -> dict:
    """Collects client profile, clinical entries, intake notes, questionnaires,
    and prior consultations strictly recorded on or before consultation_point."""
    with vault_connection(practitioner_id) as conn:
        client = conn.execute(
            "SELECT id, name, email, dob, country, created_at FROM clients WHERE id = %s",
            (client_id,),
        ).fetchone()
        if not client:
            return {}

        entries = conn.execute(
            "SELECT id, kind, content, created_at FROM record_entries "
            "WHERE client_id = %s AND created_at <= %s ORDER BY created_at ASC",
            (client_id, consultation_point),
        ).fetchall()

        intake_notes = conn.execute(
            "SELECT theme, note, updated_at FROM intake_notes "
            "WHERE client_id = %s AND updated_at <= %s ORDER BY theme ASC",
            (client_id, consultation_point),
        ).fetchall()

        questionnaire = conn.execute(
            "SELECT questionnaire_id, answers_json, submitted_at FROM questionnaire_responses "
            "WHERE client_id = %s AND submitted_at <= %s ORDER BY submitted_at DESC LIMIT 1",
            (client_id, consultation_point),
        ).fetchone()

        # Deliberately NOT s.initial_summary: that column is itself a full
        # opening briefing which, for a prior session, already recursed
        # through everything before it. Embedding it here would re-embed the
        # entire trajectory on every new session and compound without bound.
        # The short "summary" (written once by the Summariser, if ever run)
        # is the only prior-session text that belongs in this history.
        prior_sessions = conn.execute(
            """
            SELECT s.id, s.title, s.started_at, s.status,
                   (SELECT count(*) FROM session_turns t WHERE t.session_id = s.id) AS turns,
                   (SELECT e.content FROM record_entries e
                       WHERE e.session_id = s.id AND e.kind = 'session_summary'
                       ORDER BY e.created_at DESC LIMIT 1) AS summary
            FROM sessions s
            WHERE s.client_id = %s AND s.started_at < %s
            ORDER BY s.started_at ASC
            """,
            (client_id, consultation_point),
        ).fetchall()

        # specs/v9/03 — the living lab-marker state, as of this consult
        # point (not "right now"), same reproducibility contract every
        # other query in this function already honors: a past session's
        # briefing must not silently pick up a marker recorded later.
        lab_state = conn.execute(
            f"SELECT {_CLINICAL_STATE_COLUMNS} FROM client_clinical_state "
            "WHERE client_id = %s AND valid_from <= %s "
            "AND (valid_to IS NULL OR valid_to > %s) ORDER BY display_label",
            (client_id, consultation_point, consultation_point),
        ).fetchall()

    parsed_answers = {}
    if questionnaire and questionnaire["answers_json"]:
        try:
            parsed_answers = json.loads(questionnaire["answers_json"])
        except Exception:
            parsed_answers = {}

    return {
        "client": dict(client),
        "entries": [dict(e) for e in entries],
        "intake_notes": [dict(n) for n in intake_notes],
        "questionnaire": {
            "id": questionnaire["questionnaire_id"],
            "submitted_at": questionnaire["submitted_at"],
            "answers": parsed_answers,
        } if questionnaire else None,
        "prior_sessions": [dict(s) for s in prior_sessions],
        "lab_state": [dict(m) for m in lab_state],
    }


def get_session(practitioner_id: str, session_id: str) -> dict | None:
    with vault_connection(practitioner_id) as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = %s",
                           (session_id,)).fetchone()
        if row is None:
            return None
        turns = conn.execute(
            "SELECT question, answer, payload, created_at FROM session_turns "
            "WHERE session_id = %s ORDER BY ordinal", (session_id,)).fetchall()
    return {**dict(row), "turns": [
        {"question": t["question"], "answer": t["answer"],
         "created_at": t["created_at"], **json.loads(t["payload"])}
        for t in turns]}


def session_history(practitioner_id: str, session_id: str) -> list[dict]:
    """Prior turns, in the shape the Librarian and Specialist expect."""
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT question, answer FROM session_turns WHERE session_id = %s "
            "ORDER BY ordinal", (session_id,)).fetchall()
    return [dict(r) for r in rows]


def session_transcript(practitioner_id: str, session_id: str) -> str:
    """The Summariser's input. Includes each turn's Checker verdict when it
    wasn't a clean 'pass' — a session summary written into the permanent
    patient record should carry a trace that an answer had been flagged as
    containing an unsupported claim."""
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT question, answer, payload FROM session_turns "
            "WHERE session_id = %s ORDER BY ordinal", (session_id,)).fetchall()
    parts = []
    for r in rows:
        payload = json.loads(r["payload"]) if r["payload"] else {}
        check = payload.get("check") or {}
        verdict = check.get("verdict")
        flag = ""
        if verdict and verdict != "pass":
            unsupported = check.get("unsupported") or []
            flag = f"\n\n[Internal accuracy check flagged this answer as '{verdict}'"
            if unsupported:
                flag += ": " + "; ".join(unsupported)
            flag += "]"
        parts.append(f"Question: {r['question']}\n\nAnswer:\n{r['answer']}{flag}")
    return "\n\n".join(parts)


def session_has_flagged_turn(practitioner_id: str, session_id: str) -> bool:
    """True if any turn's Checker verdict wasn't a clean 'pass' — used to
    append a deterministic note to a session summary rather than relying on
    the Summariser to choose to mention it."""
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT payload FROM session_turns WHERE session_id = %s",
            (session_id,)).fetchall()
    for r in rows:
        payload = json.loads(r["payload"]) if r["payload"] else {}
        verdict = (payload.get("check") or {}).get("verdict")
        if verdict and verdict != "pass":
            return True
    return False


def log(practitioner_id: str, actor: str, action: str, detail: str,
        client_id: str | None = None) -> None:
    """Record a client-touching event inside the vault."""
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO audit_events (id, ts, actor, action, detail, client_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), _now(), actor, action, detail, client_id),
        )


def audit(practitioner_id: str, limit: int = 100) -> list[dict]:
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT id, ts, actor, action, detail, client_id FROM audit_events "
            "ORDER BY ts DESC LIMIT %s",
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
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO questionnaire_responses (id, client_id, questionnaire_id,"
            " questionnaire_version, answers_json, submitted_at) VALUES"
            " (%(id)s, %(client_id)s, %(questionnaire_id)s, %(questionnaire_version)s,"
            " %(answers_json)s, %(submitted_at)s)",
            row,
        )
    return {**row, "answers": answers}


def has_questionnaire_responses(practitioner_id: str, questionnaire_id: str) -> bool:
    """Whether anyone has ever submitted this exact questionnaire — the
    deciding factor (app/main.py's me_edit_questionnaire) between editing
    it in place and creating a new version: once a real response exists,
    its answers are keyed against this questionnaire's current question
    ids, and mutating those out from under it would make that historical
    response impossible to interpret correctly."""
    with vault_connection(practitioner_id) as conn:
        row = conn.execute(
            "SELECT 1 FROM questionnaire_responses WHERE questionnaire_id = %s LIMIT 1",
            (questionnaire_id,),
        ).fetchone()
    return row is not None


def create_intake_link(
    practitioner_id: str, token: str, kind: str, questionnaire_id: str | None = None,
    questionnaire_version: int | None = None, client_id: str | None = None,
) -> dict:
    row = {"token": token, "kind": kind, "questionnaire_id": questionnaire_id,
           "questionnaire_version": questionnaire_version, "client_id": client_id,
           "draft_answers_json": "{}", "status": "active", "created_at": _now(),
           "submitted_at": None}
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO intake_links (token, kind, questionnaire_id, "
            "questionnaire_version, client_id, draft_answers_json, status, "
            "created_at, submitted_at) VALUES (%(token)s, %(kind)s, "
            "%(questionnaire_id)s, %(questionnaire_version)s, %(client_id)s, "
            "%(draft_answers_json)s, %(status)s, %(created_at)s, %(submitted_at)s)",
            row,
        )
    return get_intake_link(practitioner_id, token)


def get_intake_link(practitioner_id: str, token: str) -> dict | None:
    with vault_connection(practitioner_id) as conn:
        row = conn.execute(
            "SELECT * FROM intake_links WHERE token = %s", (token,)
        ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["draft_answers"] = json.loads(data.pop("draft_answers_json") or "{}")
    return data


def save_intake_draft(practitioner_id: str, token: str, answers: dict) -> None:
    """Never touches `status` — an autosave can't resurrect or submit a
    link, it only ever updates an already-active one."""
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "UPDATE intake_links SET draft_answers_json = %s "
            "WHERE token = %s AND status = 'active'",
            (json.dumps(answers), token),
        )


def submit_intake_link(practitioner_id: str, token: str, client_id: str) -> None:
    """The one-way flip that makes a link one-time. `client_id` is passed
    in rather than assumed already set on the row, since an 'initial'-kind
    link only gets one once the client record is created from its answers."""
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "UPDATE intake_links SET status = 'submitted', submitted_at = %s, "
            "client_id = %s WHERE token = %s",
            (_now(), client_id, token),
        )


def list_intake_links(practitioner_id: str, client_id: str) -> list[dict]:
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT * FROM intake_links WHERE client_id = %s ORDER BY created_at DESC",
            (client_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_questionnaire_response(practitioner_id: str, client_id: str) -> dict | None:
    with vault_connection(practitioner_id) as conn:
        row = conn.execute(
            "SELECT * FROM questionnaire_responses WHERE client_id = %s "
            "ORDER BY submitted_at DESC LIMIT 1",
            (client_id,),
        ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["answers"] = json.loads(data.pop("answers_json"))
    return data


def mark_intake_viewed(practitioner_id: str, client_id: str) -> None:
    """Mark a client's latest questionnaire response as viewed — called when
    a practitioner opens their intake review, so the unviewed-count badge
    clears without needing a separate explicit action."""
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "UPDATE questionnaire_responses SET viewed_at = %s WHERE id = ("
            "  SELECT id FROM questionnaire_responses WHERE client_id = %s "
            "  ORDER BY submitted_at DESC LIMIT 1)",
            (_now(), client_id),
        )


def count_unviewed_intake(practitioner_id: str) -> int:
    """Clients whose most recent questionnaire response hasn't been viewed."""
    with vault_connection(practitioner_id) as conn:
        row = conn.execute(
            """
            SELECT count(*) AS n FROM questionnaire_responses qr
            WHERE qr.viewed_at IS NULL
              AND qr.submitted_at = (
                  SELECT max(qr2.submitted_at) FROM questionnaire_responses qr2
                  WHERE qr2.client_id = qr.client_id)
            """
        ).fetchone()
    return row["n"] if row else 0


# --- Uploaded files -------------------------------------------------------------

def save_uploaded_file(
    practitioner_id: str, client_id: str, original_name: str, media_type: str,
    storage_path: str, extracted_text: str | None = None,
    extraction_status: str = "pending", category: str = "document",
) -> dict:
    row = {"id": str(uuid.uuid4()), "client_id": client_id,
           "original_name": original_name, "media_type": media_type,
           "storage_path": storage_path, "uploaded_at": _now(),
           "extracted_text": extracted_text, "extraction_status": extraction_status,
           "category": category}
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO uploaded_files (id, client_id, original_name, "
            "media_type, storage_path, uploaded_at, extracted_text, extraction_status, category) "
            "VALUES (%(id)s, %(client_id)s, %(original_name)s, %(media_type)s, "
            "%(storage_path)s, %(uploaded_at)s, %(extracted_text)s, %(extraction_status)s, %(category)s)",
            row,
        )
    return row


def list_uploaded_files(practitioner_id: str, client_id: str) -> list[dict]:
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT * FROM uploaded_files WHERE client_id = %s "
            "ORDER BY uploaded_at DESC",
            (client_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_uploaded_file(practitioner_id: str, file_id: str, client_id: str | None = None) -> dict | None:
    """One uploaded-file row, including its storage_path — for serving the
    actual bytes back. `client_id`, when given, scopes the lookup so a
    client can only ever fetch their own file, and a practitioner's
    client-facing route can't be pointed at another client's upload by
    guessing a file id."""
    with vault_connection(practitioner_id) as conn:
        if client_id is not None:
            row = conn.execute(
                "SELECT * FROM uploaded_files WHERE id = %s AND client_id = %s",
                (file_id, client_id)).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM uploaded_files WHERE id = %s", (file_id,)).fetchone()
    return dict(row) if row else None


def link_uploaded_file_to_entry(practitioner_id: str, file_id: str, entry_id: str) -> None:
    """Records which record_entries row (kind='document' or 'lab') this
    upload is represented by in the unified Record timeline — the reverse
    direction of client_clinical_state.source_entry_id, deliberately plain
    TEXT with no FK: delete_client()/delete_entry() delete record_entries
    before uploaded_files, so a FK here would break that ordering."""
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "UPDATE uploaded_files SET record_entry_id = %s WHERE id = %s",
            (entry_id, file_id),
        )


def save_document_insights(practitioner_id: str, file_id: str, *, doc_type: str,
                           summary: str, highlights: list[dict]) -> None:
    """Written by app/reasoning/document_insights.py's classify_document, in
    the background, well after the file itself was already saved — see
    that module's docstring for the full best-effort contract."""
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "UPDATE uploaded_files SET ai_doc_type = %s, ai_summary = %s, "
            "ai_highlights_json = %s, ai_classified_at = %s WHERE id = %s",
            (doc_type, summary, json.dumps(highlights), _now(), file_id),
        )


def get_client_record(practitioner_id: str, client_id: str) -> dict:
    """Everything the Record tab renders, assembled server-side in one call
    — same "several sources into one dict" shape as
    get_patient_history_up_to(), scoped to right now rather than a
    historical consult point. Each entry carries a "file" sub-dict (AI
    doc_type/summary/highlights, plus enough to link to the file) when
    it's backed by an upload."""
    with vault_connection(practitioner_id) as conn:
        entries = conn.execute(
            "SELECT * FROM record_entries WHERE client_id = %s AND kind != 'session_summary' "
            "ORDER BY created_at DESC",
            (client_id,),
        ).fetchall()
        files = conn.execute(
            "SELECT id, record_entry_id, original_name, media_type, category, "
            "ai_doc_type, ai_summary, ai_highlights_json, ai_classified_at "
            "FROM uploaded_files WHERE client_id = %s AND record_entry_id IS NOT NULL",
            (client_id,),
        ).fetchall()
        clinical_state = conn.execute(
            f"SELECT {_CLINICAL_STATE_COLUMNS} FROM client_clinical_state "
            "WHERE client_id = %s AND valid_to IS NULL ORDER BY display_label",
            (client_id,),
        ).fetchall()
    files_by_entry_id = {f["record_entry_id"]: dict(f) for f in files}
    out_entries = []
    for e in entries:
        row = dict(e)
        file_meta = files_by_entry_id.get(e["id"])
        if file_meta:
            file_meta["ai_highlights"] = json.loads(file_meta.pop("ai_highlights_json") or "[]")
            row["file"] = file_meta
        out_entries.append(row)
    return {"entries": out_entries, "clinical_state": [dict(r) for r in clinical_state]}


def _vec_literal(embedding: list[float]) -> str:
    # Same reasoning as app/retrieval/pgvector_store.py's own helper:
    # psycopg2 has no built-in adapter for pgvector's `vector` type, so a
    # bound string parameter cast with ::vector avoids the extra
    # `pgvector` package dependency for what's otherwise one line.
    return "[" + ",".join(str(x) for x in embedding) + "]"


def save_client_document_chunks(
    practitioner_id: str, client_id: str, file_id: str, file_name: str,
    chunks: list[dict],
) -> None:
    """`chunks` is [{"text", "embedding"}, ...] — called once at upload
    time (app/main.py's _save_uploaded_file), not re-chunked per consult
    call. Replaces any existing chunks for this file first so re-
    uploading the same file_id (not currently possible from the UI, but
    cheap to make safe) doesn't accumulate duplicates."""
    if not chunks:
        return
    with vault_connection(practitioner_id) as conn:
        conn.execute("DELETE FROM client_document_chunks WHERE file_id = %s", (file_id,))
        for i, c in enumerate(chunks):
            conn.execute(
                "INSERT INTO client_document_chunks "
                "(id, client_id, file_id, file_name, chunk_index, text, embedding) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s::vector)",
                (str(uuid.uuid4()), client_id, file_id, file_name, i, c["text"],
                 _vec_literal(c["embedding"])),
            )


def search_client_documents(
    practitioner_id: str, client_id: str, query_embedding: list[float], top_k: int = 8,
) -> list[dict]:
    """Nearest-neighbor search (cosine distance) scoped to one client's
    uploaded-document chunks — the question-scoped alternative to
    app/patient/context.py concatenating every uploaded document's full
    text into every prompt. A sequential scan is fine at today's scale
    (one client's documents, not the whole library) — an ivfflat/hnsw
    index is the obvious next step if a single client's own document
    count ever grows large enough for that to matter, not added
    preemptively, same call app/retrieval/pgvector_store.py's search()
    already makes for the library-wide table."""
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            """
            SELECT file_id, file_name, chunk_index, text,
                   1 - (embedding <=> %s::vector) AS score
            FROM client_document_chunks
            WHERE client_id = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (_vec_literal(query_embedding), client_id, _vec_literal(query_embedding), top_k),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_client_document_chunks(practitioner_id: str, file_id: str) -> None:
    with vault_connection(practitioner_id) as conn:
        conn.execute("DELETE FROM client_document_chunks WHERE file_id = %s", (file_id,))


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
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO session_documents (id, session_id, client_id, kind, "
            "status, content, updated_at) VALUES (%(id)s, %(session_id)s, %(client_id)s, "
            "%(kind)s, %(status)s, %(content)s, %(updated_at)s) "
            "ON CONFLICT (session_id, kind) DO UPDATE SET "
            "status = EXCLUDED.status, content = EXCLUDED.content, "
            "updated_at = EXCLUDED.updated_at",
            row,
        )
    return get_document(practitioner_id, session_id, kind)


def save_pdf_cache(
    practitioner_id: str, session_id: str, kind: str, source_hash: str, pdf_html: str,
) -> None:
    """Records the Claude-tidied HTML a PDF was last generated from, keyed
    by a hash of the document's own `content` at that moment — see
    app/pdf_tidy.py. Deliberately a plain UPDATE, not folded into
    save_document's own upsert: a manual edit or autosave shouldn't have
    to know or care about this cache, only the PDF route does."""
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "UPDATE session_documents SET pdf_html = %s, pdf_source_hash = %s "
            "WHERE session_id = %s AND kind = %s",
            (pdf_html, source_hash, session_id, kind),
        )


def get_document(practitioner_id: str, session_id: str, kind: str) -> dict | None:
    with vault_connection(practitioner_id) as conn:
        row = conn.execute(
            "SELECT * FROM session_documents WHERE session_id = %s AND kind = %s",
            (session_id, kind),
        ).fetchone()
    return dict(row) if row else None


def list_documents(practitioner_id: str, client_id: str) -> list[dict]:
    """All documents across a client's sessions, newest first — the
    reports & documents side panel."""
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT d.*, s.title AS session_title FROM session_documents d "
            "JOIN sessions s ON s.id = d.session_id "
            "WHERE d.client_id = %s ORDER BY d.updated_at DESC",
            (client_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def save_asset(practitioner_id: str, session_id: str, client_id: str, asset_id: str, filename: str) -> dict:
    row = {"id": asset_id, "session_id": session_id, "client_id": client_id,
           "filename": filename, "created_at": _now()}
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO session_assets (id, session_id, client_id, filename, created_at) "
            "VALUES (%(id)s, %(session_id)s, %(client_id)s, %(filename)s, %(created_at)s)",
            row,
        )
    return row


def get_asset(practitioner_id: str, session_id: str, asset_id: str) -> dict | None:
    with vault_connection(practitioner_id) as conn:
        row = conn.execute(
            "SELECT * FROM session_assets WHERE session_id = %s AND id = %s",
            (session_id, asset_id),
        ).fetchone()
    return dict(row) if row else None


def list_assets(practitioner_id: str, session_id: str) -> list[dict]:
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT * FROM session_assets WHERE session_id = %s ORDER BY created_at",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# --- Intake notes (clinician notes per questionnaire theme) --------------------

def upsert_intake_note(practitioner_id: str, client_id: str, theme: str, note: str) -> dict:
    row = {"client_id": client_id, "theme": theme, "note": note, "updated_at": _now()}
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO intake_notes (client_id, theme, note, updated_at) "
            "VALUES (%(client_id)s, %(theme)s, %(note)s, %(updated_at)s) "
            "ON CONFLICT (client_id, theme) DO UPDATE SET "
            "note = EXCLUDED.note, updated_at = EXCLUDED.updated_at",
            row,
        )
    return row


def list_intake_notes(practitioner_id: str, client_id: str) -> dict:
    """Returns {theme: note} for a client."""
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute(
            "SELECT theme, note FROM intake_notes WHERE client_id = %s",
            (client_id,),
        ).fetchall()
    return {r["theme"]: r["note"] for r in rows}


# --- Source weights (practitioner's own view of the shared library) -----------

def get_source_weights(practitioner_id: str) -> dict:
    """Returns {source_id: weight} — this practitioner's own overrides only."""
    with vault_connection(practitioner_id) as conn:
        rows = conn.execute("SELECT source_id, weight FROM source_weights").fetchall()
    return {r["source_id"]: r["weight"] for r in rows}


def set_source_weight(practitioner_id: str, source_id: str, weight: int) -> dict:
    if not 1 <= weight <= 10:
        raise ValueError("weight must be between 1 and 10")
    row = {"source_id": source_id, "weight": weight, "updated_at": _now()}
    with vault_connection(practitioner_id) as conn:
        conn.execute(
            "INSERT INTO source_weights (source_id, weight, updated_at) "
            "VALUES (%(source_id)s, %(weight)s, %(updated_at)s) "
            "ON CONFLICT (source_id) DO UPDATE SET "
            "weight = EXCLUDED.weight, updated_at = EXCLUDED.updated_at",
            row,
        )
    return row
