"""The core store: shared, cross-tenant data — practitioners, plans, contact
forms, questionnaires, site stats, and the two tables the v2 spec's schema
table doesn't name but real login requires:

- `admins`: the spec says admin has its own credentials but never says where
  an admin account lives; `practitioners` doesn't fit (it carries plan and
  public-profile fields that make no sense for an admin).
- `client_directory`: clients live entirely inside their practitioner's
  vault (correctly — that's the isolation boundary), but a login request
  arrives with just an email and needs to know which vault schema to open
  before any vault can be queried. This table is a routing pointer only,
  never clinical content.

specs/v6 — this used to be its own SQLite file (data/core.db); it's now
the `public` schema of the shared Postgres database (app/db.py). Every
function signature and return shape is unchanged, so nothing outside this
module (auth.py, billing.py, main.py) needed to change.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from .db import core_connection

STATUSES = ("pending", "approved", "rejected", "suspended")
PLANS = ("basic", "pro")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_schema() -> None:
    with core_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
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
            -- CREATE TABLE IF NOT EXISTS above is a no-op for a table that
            -- already existed before per-practitioner library upload was
            -- added, same gap questionnaires.practitioner_id and
            -- vault.py's clients.active had — apply it explicitly too.
            -- An explicit per-practitioner grant, not a blanket Pro-plan
            -- perk: a superadmin/admin decides WHICH practitioners get it.
            ALTER TABLE practitioners ADD COLUMN IF NOT EXISTS
                can_upload_library BOOLEAN NOT NULL DEFAULT FALSE;

            -- specs/v7/06 — the onboarding tour's "has this account
            -- already dismissed/finished the first-run tour" flag.
            -- Persisted server-side, not localStorage — a practitioner
            -- (or admin, or client) switching devices shouldn't see the
            -- tour replay from scratch, and a plain boolean is enough
            -- since each account type only ever has one portal's tour
            -- relevant to it (no multi-portal case to track per account).
            ALTER TABLE admins ADD COLUMN IF NOT EXISTS
                tour_completed BOOLEAN NOT NULL DEFAULT FALSE;
            ALTER TABLE practitioners ADD COLUMN IF NOT EXISTS
                tour_completed BOOLEAN NOT NULL DEFAULT FALSE;

            -- specs/v8 §4.1 — some admins also hold a practitioner profile
            -- (not all — an optional link, set/cleared by a superadmin).
            -- One-directional (admins -> practitioners) is enough: the
            -- only lookup this ever needs is "does this admin also have a
            -- practitioner view," never the reverse.
            ALTER TABLE admins ADD COLUMN IF NOT EXISTS
                linked_practitioner_id TEXT REFERENCES practitioners(id);

            -- specs/v8 §8.3/§8.1 — a practitioner opts in explicitly before
            -- the public directory or landing page highlights them as
            -- taking new clients; defaults to FALSE, never auto-listed.
            ALTER TABLE practitioners ADD COLUMN IF NOT EXISTS
                accepting_new_clients BOOLEAN NOT NULL DEFAULT FALSE;

            -- Consult Draft Editor — a practitioner's own letterhead logo,
            -- shown at the top of every clinician note / client report they
            -- produce. Nullable: most practitioners won't set one right away.
            ALTER TABLE practitioners ADD COLUMN IF NOT EXISTS
                logo_path TEXT;

            -- Routing only: which vault schema a client's login belongs
            -- to. No clinical content — that lives in the vault itself.
            CREATE TABLE IF NOT EXISTS client_directory (
                email TEXT PRIMARY KEY,
                practitioner_id TEXT NOT NULL,
                client_id TEXT NOT NULL
            );

            -- Same routing-pointer role as client_directory above: a
            -- Client Intake Links token alone doesn't say which
            -- practitioner's vault schema holds the actual link row
            -- (draft answers, status) — this table is the one place that
            -- cross-schema lookup can happen. No clinical content here either.
            CREATE TABLE IF NOT EXISTS intake_link_directory (
                token TEXT PRIMARY KEY,
                practitioner_id TEXT NOT NULL
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
                is_active BOOLEAN NOT NULL DEFAULT FALSE,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            -- CREATE TABLE IF NOT EXISTS above is a no-op for a table that
            -- already existed before practitioner-owned questionnaires were
            -- added, same gap app/vault.py's `active` column has for
            -- `clients` — so apply it explicitly for a pre-existing table
            -- too. NULL means the admin-curated global default.
            ALTER TABLE questionnaires ADD COLUMN IF NOT EXISTS
                practitioner_id TEXT REFERENCES practitioners(id);

            CREATE TABLE IF NOT EXISTS questionnaire_questions (
                id TEXT PRIMARY KEY,
                questionnaire_id TEXT NOT NULL REFERENCES questionnaires(id),
                ordinal INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                input_type TEXT NOT NULL,
                options_json TEXT NOT NULL DEFAULT '[]',
                theme TEXT NOT NULL DEFAULT 'General'
            );
            CREATE INDEX IF NOT EXISTS questions_by_questionnaire
                ON questionnaire_questions(questionnaire_id, ordinal);

            -- Client Intake Links — 'initial' (no client record exists yet;
            -- submitting one creates it) vs 'followup' (tied to an existing
            -- client). Defaults to 'followup' since every questionnaire
            -- before this existed was answered by an already-signed-up client.
            ALTER TABLE questionnaires ADD COLUMN IF NOT EXISTS
                kind TEXT NOT NULL DEFAULT 'followup';
            -- A practitioner's way to retire a questionnaire without a hard
            -- delete — intake_links and questionnaire_responses reference
            -- a questionnaire_id with no FK (they live in a different
            -- per-practitioner vault database entirely), so deleting the
            -- row outright would silently orphan real historical client
            -- data. Archiving just hides it from the active list; nothing
            -- already sent or answered is affected.
            ALTER TABLE questionnaires ADD COLUMN IF NOT EXISTS
                archived BOOLEAN NOT NULL DEFAULT FALSE;
            -- Which new-client field (if any) this question's answer fills
            -- in on submission of an 'initial'-kind questionnaire — NULL for
            -- every ordinary question. Lets the backend read the client's
            -- name/email straight off a designated answer instead of
            -- guessing from free-text prompts.
            ALTER TABLE questionnaire_questions ADD COLUMN IF NOT EXISTS
                maps_to TEXT;

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

            -- An uploaded/pasted item sitting reviewable before an admin
            -- explicitly promotes it into the real knowledge graph.
            -- pages_json — a JSON list of [page_number|null, text] pairs.
            CREATE TABLE IF NOT EXISTS staged_sources (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,               -- 'file' | 'text' | 'scraped_url'
                filename TEXT,
                source_url TEXT,                  -- set only for kind='scraped_url'
                media_type TEXT,
                pages_json TEXT NOT NULL,
                char_count INTEGER NOT NULL,
                page_count INTEGER,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS staged_sources_by_created
                ON staged_sources(created_at);

            -- A backgrounded promotion of a staged item into the real
            -- knowledge graph (main.py's _run_staged_ingest_job) — split out
            -- of the request/response cycle because a large document's
            -- Reader/embed/graph-extraction/Neo4j-write chain can run past
            -- nginx's proxy_read_timeout. One row per in-flight (or
            -- finished) promotion so a client can poll it, and so progress
            -- survives a page reload instead of living only in memory.
            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                id TEXT PRIMARY KEY,
                staged_id TEXT NOT NULL,
                owner TEXT,              -- practitioner_id; NULL = admin-initiated
                filename TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',   -- running | done | error
                step TEXT NOT NULL DEFAULT 'queued',      -- queued | reading | chunking | embedding | extracting_graph | writing | done | error
                step_detail TEXT,        -- e.g. "7 of 42 passages" during extracting_graph
                error_message TEXT,
                result_document_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ingestion_jobs_by_staged ON ingestion_jobs(staged_id);
            CREATE INDEX IF NOT EXISTS ingestion_jobs_by_owner ON ingestion_jobs(owner, created_at);

            -- Small key/value store for superadmin-toggled settings that
            -- don't warrant their own table — e.g. llm_provider (app/
            -- clients/llm_client.py), switching the AI team's chat roles
            -- between Nebius and Anthropic without redeploying.
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            -- Which practitioners an admin has granted access to a
            -- private document (specs/v6.9/01) — an admin's own grant,
            -- not a practitioner's own preference, so this lives in the
            -- public schema, not inside app/vault.py's per-practitioner
            -- vault_<id> schema the way source_weights does. The
            -- document itself lives in Neo4j, not Postgres, so
            -- document_id is a plain string reference, no FK — a stale
            -- row left behind by a deleted document is harmless dead
            -- data, same category originals.delete()'s docstring already
            -- accepts for an orphaned original file.
            CREATE TABLE IF NOT EXISTS document_access (
                document_id TEXT NOT NULL,
                practitioner_id TEXT NOT NULL REFERENCES practitioners(id),
                granted_at TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                PRIMARY KEY (document_id, practitioner_id)
            );
            CREATE INDEX IF NOT EXISTS document_access_by_practitioner
                ON document_access(practitioner_id);
            """
        )
        # Every deployment needs at least one superadmin able to manage
        # other admins. If none exists (fresh install), promote the
        # earliest-created admin automatically rather than leaving every
        # admin locked out.
        has_superadmin = conn.execute(
            "SELECT 1 FROM admins WHERE role = 'superadmin' LIMIT 1"
        ).fetchone()
        if not has_superadmin:
            oldest = conn.execute(
                "SELECT id FROM admins ORDER BY created_at LIMIT 1"
            ).fetchone()
            if oldest:
                conn.execute(
                    "UPDATE admins SET role = 'superadmin' WHERE id = %s",
                    (oldest["id"],))


def ping() -> bool:
    with core_connection() as conn:
        conn.execute("SELECT 1")
    return True


def log(actor: str, action: str, detail: str) -> None:
    with core_connection() as conn:
        conn.execute(
            "INSERT INTO audit_events (id, ts, actor, action, detail) "
            "VALUES (%s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), _now(), actor, action, detail),
        )


def list_audit_events(limit: int = 50, offset: int = 0) -> list[dict]:
    """Read back what log() writes — practitioner/admin-management events
    (approvals, plan changes, admin created/role-changed/suspended,
    questionnaire edits). Distinct from the Neo4j library-only audit trail
    store.audit() covers (GET /api/audit) — see that route's docstring."""
    with core_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_events ORDER BY ts DESC LIMIT %s OFFSET %s",
            (limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]


def count_audit_events() -> int:
    with core_connection() as conn:
        return conn.execute("SELECT count(*) AS n FROM audit_events").fetchone()["n"]


# --- Settings --------------------------------------------------------------

def get_setting(key: str, default: str) -> str:
    with core_connection() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = %s", (key,)
        ).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with core_connection() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (%s, %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (key, value),
        )


# --- Private knowledge base access (specs/v6.9/01) --------------------------

def get_document_access(document_id: str) -> list[str]:
    """Practitioner ids currently granted access to this document —
    pre-checks a grant-editor dialog with who already has it."""
    with core_connection() as conn:
        rows = conn.execute(
            "SELECT practitioner_id FROM document_access WHERE document_id = %s",
            (document_id,),
        ).fetchall()
    return [r["practitioner_id"] for r in rows]


def set_document_access(document_id: str, practitioner_ids: list[str], granted_by: str) -> None:
    """Replaces the full grant list for one document in one transaction —
    same simplicity can_upload_library's single-flag-flip already has,
    not an incremental add/remove diff (specs/v6.9/01)."""
    with core_connection() as conn:
        conn.execute("DELETE FROM document_access WHERE document_id = %s", (document_id,))
        for practitioner_id in practitioner_ids:
            conn.execute(
                "INSERT INTO document_access (document_id, practitioner_id, granted_at, granted_by) "
                "VALUES (%s, %s, %s, %s)",
                (document_id, practitioner_id, _now(), granted_by),
            )
    log(granted_by, "set document access", f"{document_id} → {len(practitioner_ids)} practitioner(s)")


def get_accessible_document_ids(practitioner_id: str) -> set[str]:
    """Every document this practitioner has an explicit grant for —
    threaded through retrieval (seed search, every traversal hop,
    general lookup) as the allow-list a private document needs to be
    reachable at all. Granting a public document is harmless/a no-op —
    this set only matters where a caller also checks `is_private`."""
    with core_connection() as conn:
        rows = conn.execute(
            "SELECT document_id FROM document_access WHERE practitioner_id = %s",
            (practitioner_id,),
        ).fetchall()
    return {r["document_id"] for r in rows}


# --- Admins --------------------------------------------------------------

ADMIN_ROLES = ("admin", "superadmin")


def _decode_admin(row: dict) -> dict:
    return dict(row)


def create_admin(email: str, password_hash: str, name: str, role: str = "admin") -> dict:
    if role not in ADMIN_ROLES:
        raise ValueError(f"unknown admin role: {role}")
    admin_id = str(uuid.uuid4())
    with core_connection() as conn:
        conn.execute(
            "INSERT INTO admins (id, email, password_hash, name, role, "
            "is_active, created_at) VALUES (%s, %s, %s, %s, %s, TRUE, %s)",
            (admin_id, email, password_hash, name, role, _now()),
        )
    return get_admin(admin_id)


def get_admin_by_email(email: str) -> dict | None:
    with core_connection() as conn:
        row = conn.execute(
            "SELECT * FROM admins WHERE email = %s", (email,)
        ).fetchone()
    return _decode_admin(row) if row else None


def get_admin(admin_id: str) -> dict | None:
    with core_connection() as conn:
        row = conn.execute(
            "SELECT * FROM admins WHERE id = %s", (admin_id,)
        ).fetchone()
    return _decode_admin(row) if row else None


def list_admins() -> list[dict]:
    with core_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM admins ORDER BY created_at DESC"
        ).fetchall()
    return [_decode_admin(r) for r in rows]


def _active_superadmin_count(conn, excluding: str) -> int:
    return conn.execute(
        "SELECT count(*) AS n FROM admins WHERE role = 'superadmin' AND "
        "is_active = TRUE AND id != %s", (excluding,),
    ).fetchone()["n"]


def set_admin_role(admin_id: str, role: str) -> dict | None:
    if role not in ADMIN_ROLES:
        raise ValueError(f"unknown admin role: {role}")
    with core_connection() as conn:
        row = conn.execute(
            "SELECT role FROM admins WHERE id = %s", (admin_id,)
        ).fetchone()
        if row is None:
            return None
        if row["role"] == "superadmin" and role != "superadmin" and \
                _active_superadmin_count(conn, admin_id) == 0:
            raise ValueError("cannot demote the last superadmin")
        conn.execute("UPDATE admins SET role = %s WHERE id = %s", (role, admin_id))
    log("superadmin", "admin role changed", f"{admin_id} -> {role}")
    return get_admin(admin_id)


def set_admin_active(admin_id: str, is_active: bool) -> dict | None:
    with core_connection() as conn:
        row = conn.execute(
            "SELECT role, is_active FROM admins WHERE id = %s", (admin_id,)
        ).fetchone()
        if row is None:
            return None
        if row["role"] == "superadmin" and row["is_active"] and not is_active and \
                _active_superadmin_count(conn, admin_id) == 0:
            raise ValueError("cannot suspend the last active superadmin")
        conn.execute(
            "UPDATE admins SET is_active = %s WHERE id = %s",
            (is_active, admin_id),
        )
    log("superadmin", "admin " + ("reactivated" if is_active else "suspended"), admin_id)
    return get_admin(admin_id)


def set_admin_password(admin_id: str, password_hash: str) -> None:
    with core_connection() as conn:
        conn.execute(
            "UPDATE admins SET password_hash = %s WHERE id = %s",
            (password_hash, admin_id),
        )


def set_admin_tour_completed(admin_id: str) -> None:
    with core_connection() as conn:
        conn.execute(
            "UPDATE admins SET tour_completed = TRUE WHERE id = %s", (admin_id,)
        )


def set_admin_linked_practitioner(admin_id: str, practitioner_id: str | None) -> dict | None:
    """specs/v8 §4.1 — superadmin-only link/unlink between an admin account
    and an existing practitioner profile. Does not touch the practitioner
    row at all — the link is one-directional, read only from the admin
    side (GET /api/auth/me's has_practitioner_view)."""
    with core_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM admins WHERE id = %s", (admin_id,)
        ).fetchone()
        if not exists:
            return None
        if practitioner_id is not None and conn.execute(
            "SELECT 1 FROM practitioners WHERE id = %s", (practitioner_id,)
        ).fetchone() is None:
            raise ValueError("no such practitioner")
        conn.execute(
            "UPDATE admins SET linked_practitioner_id = %s WHERE id = %s",
            (practitioner_id, admin_id),
        )
    log("superadmin", "admin<->practitioner link changed", f"{admin_id} -> {practitioner_id}")
    return get_admin(admin_id)


# --- Practitioners ---------------------------------------------------------

def _decode_practitioner(row: dict) -> dict:
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
    with core_connection() as conn:
        conn.execute(
            "INSERT INTO practitioners (id, email, password_hash, name, "
            "status, plan, bio, specialties_json, languages_json, "
            "years_experience, consultation_price_cents, created_at) "
            "VALUES (%s, %s, %s, %s, 'pending', 'basic', %s, %s, %s, %s, %s, %s)",
            (practitioner_id, email, password_hash, name, bio,
             json.dumps(specialties or []), json.dumps(languages or []),
             years_experience, consultation_price_cents, _now()),
        )
    return get_practitioner(practitioner_id)


def get_or_create_admin_practitioner_profile(admin_id: str, name: str) -> dict:
    """An admin acting as a practitioner directly (app/auth.py's
    require_practitioner/require_pro_practitioner — no separate linked
    practitioner account) still needs a real `practitioners` row under
    its own id: every route that calls get_practitioner(session["id"])
    elsewhere (not just the auth gate, which already bypasses the plan
    check) expects one back, not None. Auto-provisioned once, 'approved'/
    'pro' from the start since an admin needs no separate approval step —
    idempotent (ON CONFLICT DO NOTHING) so a second call from another
    request racing the first is harmless. password_hash is a random,
    never-verified value: this row is never logged into on its own, only
    reached via the admin's own session. email is deliberately NOT the
    admin's real email (which already has a UNIQUE row of its own in
    `admins`, and could even collide with a real practitioner's email,
    since `practitioners.email` is also UNIQUE) — a synthetic, admin_id-
    derived address keyed to this row only, guaranteed collision-free."""
    with core_connection() as conn:
        conn.execute(
            "INSERT INTO practitioners (id, email, password_hash, name, "
            "status, plan, created_at, approved_at) "
            "VALUES (%s, %s, %s, %s, 'approved', 'pro', %s, %s) "
            "ON CONFLICT (id) DO NOTHING",
            (admin_id, f"admin-{admin_id}@internal.local", uuid.uuid4().hex,
             name, _now(), _now()),
        )
    return get_practitioner(admin_id)


def get_practitioner(practitioner_id: str) -> dict | None:
    with core_connection() as conn:
        row = conn.execute(
            "SELECT * FROM practitioners WHERE id = %s", (practitioner_id,)
        ).fetchone()
    return _decode_practitioner(row) if row else None


def get_practitioner_by_email(email: str) -> dict | None:
    with core_connection() as conn:
        row = conn.execute(
            "SELECT * FROM practitioners WHERE email = %s", (email,)
        ).fetchone()
    return _decode_practitioner(row) if row else None


def list_practitioners(status: str | None = None) -> list[dict]:
    query = "SELECT * FROM practitioners"
    params: tuple = ()
    if status is not None:
        query += " WHERE status = %s"
        params = (status,)
    query += " ORDER BY created_at DESC"
    with core_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_decode_practitioner(r) for r in rows]


def approve_practitioner(practitioner_id: str) -> dict | None:
    with core_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM practitioners WHERE id = %s", (practitioner_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE practitioners SET status = 'approved', approved_at = %s "
            "WHERE id = %s", (_now(), practitioner_id),
        )
    log("admin", "practitioner approved", practitioner_id)
    return get_practitioner(practitioner_id)


def reject_practitioner(practitioner_id: str) -> dict | None:
    with core_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM practitioners WHERE id = %s", (practitioner_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE practitioners SET status = 'rejected' WHERE id = %s",
            (practitioner_id,),
        )
    log("admin", "practitioner rejected", practitioner_id)
    return get_practitioner(practitioner_id)


def suspend_practitioner(practitioner_id: str) -> dict | None:
    with core_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM practitioners WHERE id = %s", (practitioner_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE practitioners SET status = 'suspended' WHERE id = %s",
            (practitioner_id,),
        )
    log("admin", "practitioner suspended", practitioner_id)
    return get_practitioner(practitioner_id)


def set_plan(practitioner_id: str, plan: str) -> dict | None:
    if plan not in PLANS:
        raise ValueError(f"unknown plan: {plan}")
    with core_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM practitioners WHERE id = %s", (practitioner_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE practitioners SET plan = %s WHERE id = %s",
            (plan, practitioner_id),
        )
    log("admin", "practitioner plan changed", f"{practitioner_id} -> {plan}")
    return get_practitioner(practitioner_id)


def set_can_upload_library(practitioner_id: str, allowed: bool) -> dict | None:
    with core_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM practitioners WHERE id = %s", (practitioner_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE practitioners SET can_upload_library = %s WHERE id = %s",
            (allowed, practitioner_id),
        )
    log("admin", "practitioner library-upload permission changed",
        f"{practitioner_id} -> {allowed}")
    return get_practitioner(practitioner_id)


def update_practitioner_profile(practitioner_id: str, **fields) -> dict | None:
    allowed = {"name", "bio", "specialties", "languages", "years_experience",
               "consultation_price_cents", "photo_path", "accepting_new_clients",
               "logo_path"}
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
    set_clause = ", ".join(f"{col} = %s" for col in columns)
    with core_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM practitioners WHERE id = %s", (practitioner_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            f"UPDATE practitioners SET {set_clause} WHERE id = %s",
            (*columns.values(), practitioner_id),
        )
    return get_practitioner(practitioner_id)


def set_practitioner_password(practitioner_id: str, password_hash: str) -> None:
    with core_connection() as conn:
        conn.execute(
            "UPDATE practitioners SET password_hash = %s WHERE id = %s",
            (password_hash, practitioner_id),
        )


def set_practitioner_tour_completed(practitioner_id: str) -> None:
    with core_connection() as conn:
        conn.execute(
            "UPDATE practitioners SET tour_completed = TRUE WHERE id = %s",
            (practitioner_id,),
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
    set_clause = ", ".join(f"{col} = %s" for col in updates)
    with core_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM practitioners WHERE id = %s", (practitioner_id,)
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            f"UPDATE practitioners SET {set_clause} WHERE id = %s",
            (*updates.values(), practitioner_id),
        )
    return get_practitioner(practitioner_id)


def activate_pro(practitioner_id: str) -> dict:
    """Flip the plan to pro and make sure a vault schema exists.

    Idempotent: vault.ensure_schema() (CREATE SCHEMA IF NOT EXISTS under
    the hood) is safe to call whether or not the schema already exists,
    e.g. a downgrade followed by re-upgrade.
    """
    practitioner = set_plan(practitioner_id, "pro")
    if practitioner is None:
        raise ValueError(f"unknown practitioner: {practitioner_id}")
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
    with core_connection() as conn:
        conn.execute(
            "INSERT INTO contact_form_submissions (id, practitioner_id, "
            "client_name, client_email, message, status, created_at) "
            "VALUES (%(id)s, %(practitioner_id)s, %(client_name)s, %(client_email)s, "
            "%(message)s, %(status)s, %(created_at)s)",
            submission,
        )
    log("client", "contact submission received", practitioner_id)
    return submission


def list_contact_submissions(
    practitioner_id: str | None = None, status: str | None = None,
) -> list[dict]:
    where, params = [], []
    if practitioner_id:
        where.append("practitioner_id = %s")
        params.append(practitioner_id)
    if status:
        where.append("status = %s")
        params.append(status)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with core_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM contact_form_submissions {clause} "
            "ORDER BY created_at DESC",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def count_contact_submissions(
    practitioner_id: str | None = None, status: str | None = None,
) -> int:
    """Same filters as list_contact_submissions, but a count(*) instead of
    fetching every row — used by the notifications badge, which only ever
    needs a number, not each submission's name/email/message text."""
    where, params = [], []
    if practitioner_id:
        where.append("practitioner_id = %s")
        params.append(practitioner_id)
    if status:
        where.append("status = %s")
        params.append(status)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with core_connection() as conn:
        return conn.execute(
            f"SELECT count(*) AS n FROM contact_form_submissions {clause}",
            params,
        ).fetchone()["n"]


def get_contact_submission(submission_id: str, practitioner_id: str | None = None) -> dict | None:
    """One submission by id — for an ownership check, which doesn't need
    every one of a practitioner's submissions fetched just to confirm this
    id is among them."""
    query = "SELECT * FROM contact_form_submissions WHERE id = %s"
    params: tuple = (submission_id,)
    if practitioner_id is not None:
        query += " AND practitioner_id = %s"
        params = (submission_id, practitioner_id)
    with core_connection() as conn:
        row = conn.execute(query, params).fetchone()
    return dict(row) if row else None


def update_contact_status(submission_id: str, status: str) -> dict | None:
    if status not in ("new", "contacted", "closed"):
        raise ValueError(f"unknown status: {status}")
    with core_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM contact_form_submissions WHERE id = %s",
            (submission_id,),
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE contact_form_submissions SET status = %s WHERE id = %s",
            (status, submission_id),
        )
        row = conn.execute(
            "SELECT * FROM contact_form_submissions WHERE id = %s",
            (submission_id,),
        ).fetchone()
    return dict(row)


# --- Analytics ---------------------------------------------------------------

def log_profile_view(practitioner_id: str) -> None:
    with core_connection() as conn:
        conn.execute(
            "INSERT INTO profile_view_events (id, practitioner_id, ts) "
            "VALUES (%s, %s, %s)",
            (str(uuid.uuid4()), practitioner_id, _now()),
        )


def site_stats() -> dict:
    with core_connection() as conn:
        views = conn.execute(
            "SELECT count(*) AS n FROM profile_view_events"
        ).fetchone()["n"]
        contacts = conn.execute(
            "SELECT count(*) AS n FROM contact_form_submissions"
        ).fetchone()["n"]
        new_contacts = conn.execute(
            "SELECT count(*) AS n FROM contact_form_submissions WHERE status = 'new'"
        ).fetchone()["n"]
        pending_practitioners = conn.execute(
            "SELECT count(*) AS n FROM practitioners WHERE status = 'pending'"
        ).fetchone()["n"]
        approved_practitioners = conn.execute(
            "SELECT count(*) AS n FROM practitioners WHERE status = 'approved'"
        ).fetchone()["n"]
    return {
        "total_views": views, "total_contacts": contacts, "new_contacts": new_contacts,
        "pending_practitioners": pending_practitioners,
        "approved_practitioners": approved_practitioners,
    }


def practitioner_stats(practitioner_id: str) -> dict:
    with core_connection() as conn:
        views = conn.execute(
            "SELECT count(*) AS n FROM profile_view_events WHERE practitioner_id = %s",
            (practitioner_id,),
        ).fetchone()["n"]
        contacts = conn.execute(
            "SELECT count(*) AS n FROM contact_form_submissions "
            "WHERE practitioner_id = %s",
            (practitioner_id,),
        ).fetchone()["n"]
    return {"views": views, "contacts": contacts}


# --- Questionnaires (versioned) -----------------------------------------------

# "info" renders its prompt as plain instructional text and captures no
# answer (the real example form's disclaimers and consent paragraph).
# "repeater" is a question with its own sub-fields, answered as a list of
# rows — addable/removable (Medications) when its options carry no fixed
# row labels, or a pre-seeded fixed grid (Typical Workday) when they do.
QUESTION_TYPES = ("text", "number", "date", "choice", "multi_choice", "info", "repeater")
QUESTIONNAIRE_KINDS = ("initial", "followup")
# Which new-client field a question's answer maps to, for an 'initial'-kind
# questionnaire's submission — see questionnaire_questions.maps_to above.
MAPS_TO_FIELDS = ("client_name", "client_email", "client_dob", "client_country")


def _encode_options(q: dict) -> str:
    """`options_json` holds whatever shape this question's input_type
    actually needs — a plain list of choices (every question created
    before `allow_other`/`repeater` existed, and still every ordinary
    choice/multi_choice one), `{"choices", "allow_other"}` for a choice/
    multi_choice with "Other, please specify" on, or `{"columns",
    "fixed_rows"}` for a repeater's sub-field definition."""
    if q["input_type"] == "repeater":
        return json.dumps({"columns": q.get("columns", []), "fixed_rows": q.get("fixed_rows")})
    options = q.get("options", [])
    if q.get("allow_other"):
        return json.dumps({"choices": options, "allow_other": True})
    return json.dumps(options)


def _decode_question(row: dict) -> dict:
    """The inverse of _encode_options, branching the same way by
    input_type so an old caller that only ever read `options` as a plain
    array keeps working unchanged for every type but repeater."""
    d = dict(row)
    parsed = json.loads(d.pop("options_json"))
    if d["input_type"] == "repeater":
        parsed = parsed if isinstance(parsed, dict) else {}
        d["options"] = []
        d["allow_other"] = False
        d["columns"] = parsed.get("columns", [])
        d["fixed_rows"] = parsed.get("fixed_rows")
    elif isinstance(parsed, dict):
        d["options"] = parsed.get("choices", [])
        d["allow_other"] = bool(parsed.get("allow_other"))
        d["columns"] = []
        d["fixed_rows"] = None
    else:
        d["options"] = parsed if isinstance(parsed, list) else []
        d["allow_other"] = False
        d["columns"] = []
        d["fixed_rows"] = None
    return d


def _validate_questions(questions: list[dict], kind: str) -> None:
    """Shared by every write path that stores a question list — insert a
    brand-new questionnaire, mutate one in place, or duplicate one — so
    the same rules apply regardless of which of those three a caller uses."""
    if kind not in QUESTIONNAIRE_KINDS:
        raise ValueError(f"unknown questionnaire kind: {kind}")
    for q in questions:
        if q["input_type"] not in QUESTION_TYPES:
            raise ValueError(f"unknown question type: {q['input_type']}")
        maps_to = q.get("maps_to")
        if maps_to is not None and maps_to not in MAPS_TO_FIELDS:
            raise ValueError(f"unknown maps_to field: {maps_to}")
        if q["input_type"] == "repeater":
            columns = q.get("columns", [])
            if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
                raise ValueError("a repeater question's columns must be a list of strings")
            fixed_rows = q.get("fixed_rows")
            if fixed_rows is not None and (
                not isinstance(fixed_rows, list) or not all(isinstance(r, str) for r in fixed_rows)
            ):
                raise ValueError("a repeater question's fixed_rows must be a list of strings or omitted")
    if kind == "initial":
        # A Client Intake Link for this questionnaire creates the client
        # record from its answers (app/main.py's intake-submit route) —
        # it needs a designated name and email question to read those
        # from, exactly one of each, not a best guess off free-text prompts.
        mapped = [q.get("maps_to") for q in questions if q.get("maps_to")]
        if mapped.count("client_name") != 1 or mapped.count("client_email") != 1:
            raise ValueError(
                "an 'initial' questionnaire needs exactly one question "
                "mapped to client_name and one mapped to client_email")


def _replace_questions(conn, questionnaire_id: str, questions: list[dict]) -> None:
    """Shared by _insert_questionnaire and update_questionnaire_in_place —
    both ultimately just need "this id's question rows are now exactly
    this list, in this order"."""
    conn.execute("DELETE FROM questionnaire_questions WHERE questionnaire_id = %s", (questionnaire_id,))
    for ordinal, q in enumerate(questions):
        conn.execute(
            "INSERT INTO questionnaire_questions (id, questionnaire_id, "
            "ordinal, prompt, input_type, options_json, theme, maps_to) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), questionnaire_id, ordinal, q["prompt"],
             q["input_type"], _encode_options(q),
             q.get("theme") or "General", q.get("maps_to")),
        )


def _insert_questionnaire(
    title: str, version: int, created_by: str, questions: list[dict],
    practitioner_id: str | None = None, kind: str = "followup",
) -> str:
    """Insert a new questionnaire version and deactivate every other one in
    the same scope — one active questionnaire per practitioner_id (NULL
    being the admin-curated global default), not one active questionnaire
    globally."""
    _validate_questions(questions, kind)
    # No longer deactivates every other questionnaire in scope — a
    # practitioner can have as many active questionnaires (of either kind)
    # at once as they want; link generation doesn't even look at is_active
    # (app/main.py's me_create_intake_link works from any questionnaire by
    # id), so there was never a functional reason to force exclusivity
    # here, only a historical one-active-at-a-time UI convention that kept
    # silently deactivating a practitioner's OTHER kind's questionnaire
    # too. edit_questionnaire (below) still supersedes specifically the
    # one old version it's replacing — that's a real versioning concern,
    # not this.
    questionnaire_id = str(uuid.uuid4())
    with core_connection() as conn:
        conn.execute(
            "INSERT INTO questionnaires (id, title, version, is_active, "
            "created_by, created_at, practitioner_id, kind) "
            "VALUES (%s, %s, %s, TRUE, %s, %s, %s, %s)",
            (questionnaire_id, title, version, created_by, _now(), practitioner_id, kind),
        )
        _replace_questions(conn, questionnaire_id, questions)
    return questionnaire_id


def create_questionnaire(
    title: str, questions: list[dict], created_by: str,
    practitioner_id: str | None = None, kind: str = "followup",
) -> dict:
    questionnaire_id = _insert_questionnaire(
        title, 1, created_by, questions, practitioner_id, kind)
    log(created_by, "questionnaire created", questionnaire_id)
    return get_questionnaire(questionnaire_id)


def edit_questionnaire(
    questionnaire_id: str, title: str, questions: list[dict], created_by: str,
    kind: str | None = None,
) -> dict:
    """Create a new version rather than mutate the one clients already
    answered against. The new version supersedes specifically the old
    version of THIS questionnaire (deactivated below if it was active) —
    that's a real versioning concern (v1 and v2 of the same questionnaire
    both active at once makes no sense), not the broad "only one active
    questionnaire at all" exclusivity _insert_questionnaire used to
    enforce across every questionnaire in scope, which is gone now. The
    new version stays in the same practitioner_id scope as the version it
    replaces, and keeps the same kind unless a new one is given."""
    with core_connection() as conn:
        old = conn.execute(
            "SELECT version, practitioner_id, kind, is_active FROM questionnaires WHERE id = %s",
            (questionnaire_id,),
        ).fetchone()
    if old is None:
        raise ValueError(f"unknown questionnaire: {questionnaire_id}")
    new_id = _insert_questionnaire(
        title, old["version"] + 1, created_by, questions, old["practitioner_id"],
        kind if kind is not None else old["kind"])
    if old["is_active"]:
        with core_connection() as conn:
            conn.execute(
                "UPDATE questionnaires SET is_active = FALSE WHERE id = %s",
                (questionnaire_id,),
            )
    log(created_by, "questionnaire edited", f"{questionnaire_id} -> {new_id}")
    return get_questionnaire(new_id)


def update_questionnaire_in_place(
    questionnaire_id: str, title: str, questions: list[dict], created_by: str,
    kind: str | None = None,
) -> dict:
    """The edit path for the common case: nobody has answered this
    questionnaire yet, so there's no existing response whose answer keys
    depend on its current exact question list — mutating it in place (same
    id, same version) is safe, and is what a practitioner means by "edit",
    not "silently create a near-duplicate". The caller (app/main.py's
    me_edit_questionnaire) is what decides which of this or
    edit_questionnaire applies, since that decision needs
    vault.has_questionnaire_responses — a different database this module
    has no connection to."""
    with core_connection() as conn:
        old = conn.execute(
            "SELECT kind FROM questionnaires WHERE id = %s", (questionnaire_id,),
        ).fetchone()
    if old is None:
        raise ValueError(f"unknown questionnaire: {questionnaire_id}")
    effective_kind = kind if kind is not None else old["kind"]
    _validate_questions(questions, effective_kind)
    with core_connection() as conn:
        conn.execute(
            "UPDATE questionnaires SET title = %s, kind = %s WHERE id = %s",
            (title, effective_kind, questionnaire_id),
        )
        _replace_questions(conn, questionnaire_id, questions)
    log(created_by, "questionnaire updated in place", questionnaire_id)
    return get_questionnaire(questionnaire_id)


def duplicate_questionnaire(questionnaire_id: str, created_by: str, practitioner_id: str) -> dict:
    """An explicit, deliberate copy — a new id, version 1, "(copy)"
    appended to the title — for when a practitioner actually wants a
    variant without touching the original. Distinct from the old implicit
    behavior where every edit created a new row that looked like a
    duplicate; that's gone now (see update_questionnaire_in_place).

    `practitioner_id` is always the caller's own id, even when duplicating
    the admin default (practitioner_id IS NULL there) — the copy is always
    a new, editable questionnaire owned by whoever asked for it, never
    another read-only default."""
    original = get_questionnaire(questionnaire_id)
    if original is None:
        raise ValueError(f"unknown questionnaire: {questionnaire_id}")
    questions = [
        {"prompt": q["prompt"], "input_type": q["input_type"], "theme": q["theme"],
         "options": q["options"], "allow_other": q["allow_other"],
         "columns": q["columns"], "fixed_rows": q["fixed_rows"], "maps_to": q.get("maps_to")}
        for q in original["questions"]
    ]
    return create_questionnaire(
        f"{original['title']} (copy)", questions, created_by,
        practitioner_id=practitioner_id, kind=original["kind"])


def set_questionnaire_archived(questionnaire_id: str, practitioner_id: str, archived: bool) -> dict:
    """Scoped to practitioner_id so a practitioner can never archive the
    admin-curated global default (practitioner_id IS NULL there) or
    another practitioner's own questionnaire."""
    with core_connection() as conn:
        row = conn.execute(
            "UPDATE questionnaires SET archived = %s "
            "WHERE id = %s AND practitioner_id = %s RETURNING id",
            (archived, questionnaire_id, practitioner_id),
        ).fetchone()
    if row is None:
        raise ValueError(f"unknown questionnaire: {questionnaire_id}")
    log(practitioner_id, "questionnaire archived" if archived else "questionnaire unarchived", questionnaire_id)
    return get_questionnaire(questionnaire_id)


def get_questionnaire(questionnaire_id: str) -> dict | None:
    with core_connection() as conn:
        row = conn.execute(
            "SELECT * FROM questionnaires WHERE id = %s", (questionnaire_id,)
        ).fetchone()
        if row is None:
            return None
        questions = conn.execute(
            "SELECT * FROM questionnaire_questions WHERE questionnaire_id = %s "
            "ORDER BY ordinal",
            (questionnaire_id,),
        ).fetchall()
    return {**dict(row), "questions": [_decode_question(q) for q in questions]}


def list_questionnaires(
    practitioner_id: str | None = None, include_admin_default: bool = False,
    include_archived: bool = False,
) -> list[dict]:
    """With no practitioner_id: the admin listing, every questionnaire in
    every scope. With one: only that practitioner's own — never another
    practitioner's — plus the admin default too if include_admin_default
    (view-only on the caller's side; this function doesn't enforce that,
    the route layer does by never wiring edit to a questionnaire outside
    the caller's own scope). Archived ones are hidden unless
    include_archived — the admin default is never archived (a practitioner
    can't archive it), so that filter never hides it either way."""
    archived_clause = "" if include_archived else "AND archived = FALSE"
    with core_connection() as conn:
        if practitioner_id is None:
            rows = conn.execute(
                f"SELECT * FROM questionnaires WHERE TRUE {archived_clause} "
                "ORDER BY created_at DESC"
            ).fetchall()
        elif include_admin_default:
            rows = conn.execute(
                "SELECT * FROM questionnaires "
                f"WHERE (practitioner_id = %s {archived_clause} OR practitioner_id IS NULL) "
                "ORDER BY created_at DESC",
                (practitioner_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM questionnaires WHERE practitioner_id = %s {archived_clause} "
                "ORDER BY created_at DESC",
                (practitioner_id,),
            ).fetchall()
    return [dict(r) for r in rows]


# --- Client directory (routing pointer only) ----------------------------------

def add_client_directory_entry(
    email: str, practitioner_id: str, client_id: str,
) -> None:
    with core_connection() as conn:
        conn.execute(
            "INSERT INTO client_directory (email, practitioner_id, client_id) "
            "VALUES (%s, %s, %s) "
            "ON CONFLICT (email) DO UPDATE SET "
            "practitioner_id = EXCLUDED.practitioner_id, client_id = EXCLUDED.client_id",
            (email, practitioner_id, client_id),
        )


def get_client_directory_entry(email: str) -> dict | None:
    with core_connection() as conn:
        row = conn.execute(
            "SELECT * FROM client_directory WHERE email = %s", (email,)
        ).fetchone()
    return dict(row) if row else None


# --- Intake link directory (routing pointer only) -----------------------------

def add_intake_link_directory_entry(token: str, practitioner_id: str) -> None:
    with core_connection() as conn:
        conn.execute(
            "INSERT INTO intake_link_directory (token, practitioner_id) VALUES (%s, %s)",
            (token, practitioner_id),
        )


def get_intake_link_directory_entry(token: str) -> dict | None:
    with core_connection() as conn:
        row = conn.execute(
            "SELECT * FROM intake_link_directory WHERE token = %s", (token,)
        ).fetchone()
    return dict(row) if row else None


# --- Staged sources (uploaded/pasted, not yet promoted into the graph) --------

def _decode_staged(row: dict) -> dict:
    """Drops the full page text from what's returned — a staged list can
    hold many large documents, and the checklist UI only needs a short
    preview, not the whole body. get_staged_pages() below is the one call
    site that needs the real text, for promotion."""
    d = dict(row)
    pages = json.loads(d.pop("pages_json"))
    text = " ".join(t for _, t in pages if t).strip()
    d["preview"] = text[:280]
    return d


def create_staged_source(
    kind: str, filename: str | None, media_type: str | None,
    pages: list[tuple[int | None, str]], created_by: str,
    source_url: str | None = None,
) -> dict:
    if kind not in ("file", "text", "scraped_url"):
        raise ValueError(f"unknown staged source kind: {kind}")
    staged_id = str(uuid.uuid4())
    char_count = sum(len(t) for _, t in pages)
    page_count = sum(1 for n, _ in pages if n is not None)
    row = {
        "id": staged_id, "kind": kind, "filename": filename, "source_url": source_url,
        "media_type": media_type, "pages_json": json.dumps(pages), "char_count": char_count,
        "page_count": page_count, "created_at": _now(), "created_by": created_by,
    }
    with core_connection() as conn:
        conn.execute(
            "INSERT INTO staged_sources (id, kind, filename, source_url, media_type, "
            "pages_json, char_count, page_count, created_at, created_by) VALUES "
            "(%(id)s, %(kind)s, %(filename)s, %(source_url)s, %(media_type)s, "
            "%(pages_json)s, %(char_count)s, %(page_count)s, %(created_at)s, %(created_by)s)",
            row,
        )
    return get_staged_source(staged_id)


def list_staged_sources(created_by: str | None = None) -> list[dict]:
    """created_by=None is the admin view — every staged item, as today.
    A permitted practitioner passes their own id so they only ever see what
    they themselves staged, never another practitioner's or admin's.

    Each row carries its latest ingestion_jobs status/error (specs/v6.12)
    — a staged item is now shown as an in-progress card right in the
    Library grid instead of a separate reviewable list, so the frontend
    needs to tell "never actually started" (job_status is null — auto-
    kick it) apart from "errored, waiting on the admin" (job_status =
    'error' — show the error, don't silently retry) without a second
    round trip per item."""
    query = (
        "SELECT s.*, j.status AS job_status, j.step AS job_step, "
        "j.step_detail AS job_step_detail, j.error_message AS job_error_message "
        "FROM staged_sources s "
        "LEFT JOIN LATERAL ("
        "  SELECT status, step, step_detail, error_message FROM ingestion_jobs "
        "  WHERE staged_id = s.id ORDER BY created_at DESC LIMIT 1"
        ") j ON true"
    )
    params: tuple = ()
    if created_by is not None:
        query += " WHERE s.created_by = %s"
        params = (created_by,)
    query += " ORDER BY s.created_at DESC"
    with core_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_decode_staged(r) for r in rows]


def get_staged_source(staged_id: str, created_by: str | None = None) -> dict | None:
    query = "SELECT * FROM staged_sources WHERE id = %s"
    params: tuple = (staged_id,)
    if created_by is not None:
        query += " AND created_by = %s"
        params = (staged_id, created_by)
    with core_connection() as conn:
        row = conn.execute(query, params).fetchone()
    return _decode_staged(row) if row else None


def get_staged_pages(staged_id: str) -> list[list] | None:
    """The real page text, for promotion (main.py's _promote_staged_async) —
    kept separate from get_staged_source()/list_staged_sources() so an
    admin's checklist view never has to pull every staged document's full
    body over the wire just to render a list."""
    with core_connection() as conn:
        row = conn.execute(
            "SELECT pages_json FROM staged_sources WHERE id = %s", (staged_id,)
        ).fetchone()
    return json.loads(row["pages_json"]) if row else None


def delete_staged_source(staged_id: str, created_by: str | None = None) -> bool:
    query = "DELETE FROM staged_sources WHERE id = %s"
    params: tuple = (staged_id,)
    if created_by is not None:
        query += " AND created_by = %s"
        params = (staged_id, created_by)
    with core_connection() as conn:
        cur = conn.execute(query, params)
    return cur.rowcount > 0


# --- Ingestion jobs: backgrounded staged-source promotion (main.py's
# _run_staged_ingest_job) ----------------------------------------------------

def create_ingestion_job(staged_id: str, owner: str | None, filename: str) -> dict:
    """Starts 'queued' (app/ingestion/queue.py) — a worker flips it to
    'running' once it actually picks the job up, which may not be
    immediately if cfg.ingestion_concurrency's other slots are all busy.
    Distinct from `step='queued'` below, which means something narrower
    ("accepted, about to start reading") and is set by the worker itself
    right as that status flip happens — a client sees status='queued'
    the whole time it's genuinely waiting for a slot, then status=
    'running'/step='queued' for the brief moment between being picked up
    and the first real progress update."""
    job_id = str(uuid.uuid4())
    now = _now()
    row = {
        "id": job_id, "staged_id": staged_id, "owner": owner, "filename": filename,
        "status": "queued", "step": "queued", "step_detail": None,
        "error_message": None, "result_document_id": None,
        "created_at": now, "updated_at": now,
    }
    with core_connection() as conn:
        conn.execute(
            "INSERT INTO ingestion_jobs (id, staged_id, owner, filename, status, step, "
            "step_detail, error_message, result_document_id, created_at, updated_at) VALUES "
            "(%(id)s, %(staged_id)s, %(owner)s, %(filename)s, %(status)s, %(step)s, "
            "%(step_detail)s, %(error_message)s, %(result_document_id)s, %(created_at)s, "
            "%(updated_at)s)",
            row,
        )
    return get_ingestion_job(job_id)


_INGESTION_JOB_FIELDS = ("status", "step", "step_detail", "error_message", "result_document_id")


def update_ingestion_job(job_id: str, **fields) -> None:
    """Called throughout the backgrounded portion of ingestion as each stage
    completes (queued -> reading -> chunking -> embedding ->
    extracting_graph -> writing -> done/error), so a client polling
    GET /api/ingestion-jobs/{id} sees live progress instead of a single
    running -> done jump. `updated_at` is stamped here rather than left to
    the caller so every write moves it forward."""
    unknown = set(fields) - set(_INGESTION_JOB_FIELDS)
    if unknown:
        raise ValueError(f"unknown ingestion_jobs field(s): {unknown}")
    if not fields:
        return
    fields = {**fields, "updated_at": _now()}
    set_clause = ", ".join(f"{k} = %({k})s" for k in fields)
    with core_connection() as conn:
        conn.execute(
            f"UPDATE ingestion_jobs SET {set_clause} WHERE id = %(id)s",
            {**fields, "id": job_id},
        )


def get_ingestion_job(job_id: str) -> dict | None:
    with core_connection() as conn:
        row = conn.execute(
            "SELECT * FROM ingestion_jobs WHERE id = %s", (job_id,)
        ).fetchone()
    return dict(row) if row else None


def get_active_job_for_staged(staged_id: str) -> dict | None:
    """Found live, specs/v6.16: nothing stopped two ingestion jobs from
    being created for the same staged item (a double-click on Retry, or
    the page-load auto-kick racing a manual click) — the frontend's
    polling is keyed by staged_id, so starting a second job silently
    stops tracking the first. If the first then wins the Neo4j write,
    its completion is never observed; the second's ConstraintError 409
    reports the whole thing as a failure even though the document was
    actually ingested. _promote_staged_async checks this before
    creating a new job, so a duplicate attempt reattaches to the
    existing one instead of racing it."""
    with core_connection() as conn:
        row = conn.execute(
            "SELECT * FROM ingestion_jobs WHERE staged_id = %s "
            "AND status IN ('queued', 'running') ORDER BY created_at DESC LIMIT 1",
            (staged_id,),
        ).fetchone()
    return dict(row) if row else None


def cancel_active_jobs_for_staged(
    staged_id: str,
    message: str = "Ingestion stopped by user.",
    owner: str | None = None,
) -> list[str]:
    """Cancels any running or queued jobs for this staged_id by marking them
    status='error' with a clear cancellation message. Returns list of cancelled job IDs."""
    query = (
        "SELECT id FROM ingestion_jobs "
        "WHERE staged_id = %s AND status IN ('queued', 'running')"
    )
    params: list = [staged_id]
    if owner is not None:
        query += " AND owner = %s"
        params.append(owner)

    with core_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
        cancelled_ids = [r["id"] for r in rows]
        if cancelled_ids:
            update_query = (
                "UPDATE ingestion_jobs SET status = 'error', step = 'error', "
                "error_message = %s, updated_at = %s "
                "WHERE staged_id = %s AND status IN ('queued', 'running')"
            )
            update_params: list = [message, _now(), staged_id]
            if owner is not None:
                update_query += " AND owner = %s"
                update_params.append(owner)
            conn.execute(update_query, tuple(update_params))
        return cancelled_ids


def fail_orphaned_ingestion_jobs() -> int:
    """Called once at boot (app/main.py's lifespan). A job's background
    thread lives inside one worker process — a SIGHUP graceful reload
    (app/db.py's ExecReload, or the equally-hard restart before it) can
    outlast a large ingest's --graceful-timeout and kill the old worker
    mid-job, and the new worker has no way to resume a thread that died
    with it. Without this, that job's row stays 'running' forever: GET
    /api/ingestion-jobs/active keeps surfacing it, and its progress bar is
    stuck with no way to ever resolve or retry through the UI (found in
    review, right after the graceful-reload deploy work landed).

    Also covers 'queued' (app/ingestion/queue.py) — a job a worker never
    actually picked up before the process died. No partial work was
    lost for it (nothing had started), but the in-process asyncio.Queue
    it was waiting on is gone too, so it would otherwise sit at
    status='queued' forever with nothing left to ever pick it up — same
    clear-error outcome as a 'running' job, not a silent resume."""
    with core_connection() as conn:
        cur = conn.execute(
            "UPDATE ingestion_jobs SET status = 'error', step = 'error', "
            "error_message = 'Interrupted by a server restart — please retry.', "
            "updated_at = %s WHERE status IN ('running', 'queued')",
            (_now(),),
        )
        return cur.rowcount


def list_active_ingestion_jobs(owner: str | None = None) -> list[dict]:
    """owner=None (admin) sees every running job; a practitioner's own id
    scopes to just their own — same owner semantics as list_staged_sources.
    Lets the frontend reattach to an in-progress job after a page reload
    without the client having to remember a job id anywhere itself."""
    # 'queued' too, not just 'running' — found live, specs/v6.12: a job
    # still waiting for a concurrency slot (app/ingestion/queue.py) was
    # invisible to a page reload until a worker actually picked it up,
    # even though fail_orphaned_ingestion_jobs() above already treats
    # 'queued' as just as real an in-flight state as 'running'.
    query = "SELECT * FROM ingestion_jobs WHERE status IN ('running', 'queued')"
    params: tuple = ()
    if owner is not None:
        query += " AND owner = %s"
        params = (owner,)
    query += " ORDER BY created_at DESC"
    with core_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def ingestion_queue_stats(owner: str | None = None) -> dict:
    """The status bar's numbers (specs/v6.12) — queued/processing counts,
    how many characters are still waiting to be read, and a rough ETA
    from how long the last few completed jobs actually took. Duration is
    computed in Python from the ISO timestamps _now() already writes,
    not SQL date math, so this doesn't care which of sqlite/Postgres
    core_connection() is backed by this run."""
    active_filter = "status IN ('running', 'queued')"
    owner_filter = " AND owner = %s" if owner is not None else ""
    params: tuple = (owner,) if owner is not None else ()
    with core_connection() as conn:
        queued = conn.execute(
            f"SELECT status FROM ingestion_jobs WHERE {active_filter}{owner_filter}",
            params,
        ).fetchall()
        # char_count lives on staged_sources, not ingestion_jobs — joined
        # by id, same relationship _run_staged_ingest_job's own staged_id
        # lookups already rely on. A staged row still exists for exactly
        # as long as its job is active (deleted only once the job's
        # _run_ingest call actually succeeds), so this join never misses
        # an active job's size.
        chars_row = conn.execute(
            f"SELECT COALESCE(SUM(s.char_count), 0) AS total FROM ingestion_jobs j "
            f"JOIN staged_sources s ON s.id = j.staged_id WHERE j.{active_filter}{owner_filter}",
            params,
        ).fetchone()
        # Last 10 completed jobs (any owner — a small sample of only one
        # practitioner's jobs would be a noisy ETA): real wall-clock time
        # from queued to done, not a per-stage breakdown.
        recent = conn.execute(
            "SELECT created_at, updated_at FROM ingestion_jobs "
            "WHERE status = 'done' ORDER BY updated_at DESC LIMIT 10"
        ).fetchall()
    queued_count = sum(1 for r in queued if r["status"] == "queued")
    processing_count = sum(1 for r in queued if r["status"] == "running")
    durations = []
    for r in recent:
        try:
            started = datetime.fromisoformat(r["created_at"])
            finished = datetime.fromisoformat(r["updated_at"])
            durations.append((finished - started).total_seconds())
        except (TypeError, ValueError):
            continue
    avg_seconds = sum(durations) / len(durations) if durations else None
    active_count = queued_count + processing_count
    return {
        "queued_count": queued_count,
        "processing_count": processing_count,
        "total_queued_chars": int(chars_row["total"] or 0),
        "avg_seconds_per_job": avg_seconds,
        "estimated_seconds_remaining": (
            avg_seconds * active_count if avg_seconds is not None and active_count else None
        ),
    }
