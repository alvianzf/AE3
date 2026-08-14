# 02 · Data model

Three stores. The split follows v1's principle — a boundary that matters is
made structural, not promised — repeated at tenant scale instead of once
globally.

| Store | Holds | Why here |
|---|---|---|
| **Core** (SQLite, shared) | Practitioners, plans, public profiles, contact form submissions, questionnaire definitions, site statistics | Cross-tenant by nature: the directory, admin dashboards, and billing all need to query across every practitioner |
| **Neo4j** (shared) | The knowledge library — unchanged from v1 | One corpus, admin-curated, read by every Pro practitioner's Specialist calls |
| **Vault** (SQLite, one file per Pro practitioner) | That practitioner's clients, questionnaire responses, uploaded files, wearable data, consultations, vault audit | Must not be reachable from any other practitioner's code path — a missing `WHERE practitioner_id = ?` should be structurally impossible, not merely unwritten |

A **Basic** practitioner has no vault file — one is created the moment they
upgrade to Pro. There is nothing to isolate before that, since Basic carries
no clients.

---

## Core store — `data/core.db`

```sql
admins (
  id TEXT PRIMARY KEY, email UNIQUE, password_hash, name,
  role TEXT,             -- admin | superadmin — added 2026-08-13, see
                          -- 04-admin-portal.md §0
  is_active INTEGER,      -- suspended admins keep their row, login blocked
  created_at
)

practitioners (
  id TEXT PRIMARY KEY, email UNIQUE, password_hash, name,
  status TEXT,          -- pending | approved | rejected | suspended
  plan TEXT,            -- basic | pro
  photo_path, bio, specialties_json, languages_json,
  years_experience, consultation_price_cents,
  anthropic_api_key_encrypted,   -- Pro only; NULL on Basic
  stripe_customer_id, stripe_subscription_id, stripe_status,
  created_at, approved_at
)

-- Routing only: which vault a client's login belongs to, since clients
-- live entirely inside their practitioner's vault. Holds no clinical
-- content — just enough to resolve email -> (practitioner_id, client_id)
-- before any vault file is opened.
client_directory (
  email TEXT PRIMARY KEY, practitioner_id, client_id
)

contact_form_submissions (
  id TEXT PRIMARY KEY, practitioner_id, client_name, client_email,
  message, created_at, status   -- new | contacted | closed
)

questionnaires (
  id TEXT PRIMARY KEY, title, version INTEGER, is_active,
  created_by, created_at
)

questionnaire_questions (
  id TEXT PRIMARY KEY, questionnaire_id, ordinal, prompt,
  input_type,          -- text | choice | multi_choice | number | date
  options_json,
  theme TEXT NOT NULL DEFAULT 'General'   -- v2.7: groups questions for the
)                                          -- practitioner's themed intake review

profile_view_events (
  id TEXT PRIMARY KEY, practitioner_id, ts
)  -- one row per directory/detail-page view; rolled up for the admin stats page

audit_events (
  id TEXT PRIMARY KEY, ts, actor, action, detail
)  -- admin/practitioner actions on shared data: approvals, plan changes,
   -- library edits, questionnaire edits. Never a client name or clinical
   -- content — that boundary is the same one v1 drew and re-broke once
   -- (v1 07-security.md#the-leak-that-was-found). Client-touching events
   -- belong in the vault's own audit_events, not here.
```

**Editing a questionnaire creates a new version** (`version` increments, the
old row's `is_active` flips off) rather than mutating question text in
place — a client's already-submitted answers stay attached to the version
they actually answered, same reasoning as this spec set versioning itself.

**`anthropic_api_key_encrypted`** — a Pro practitioner's own key, used for
their RAG calls at consultation time. Encrypted at rest with a
platform-held key (see [10 · Security](10-security.md)); never logged, never
returned by any read endpoint once set (write-only from the client's
perspective).

**`password_hash`** (on `admins`, `practitioners`, and vault `clients`) —
never returned by any read endpoint either, on any of the three tables. This
was violated by nine routes in practice, including one public and
unauthenticated, before being found and fixed the same day it was
introduced — see [10 · Security §the leak that was
found](10-security.md#the-leak-that-was-found).

## Neo4j — the knowledge library

Unchanged from v1 ([v1/02-data-model.md](../v1/02-data-model.md)): `Source →
Chunk → Concept/Topic`, graded, admin-curated, ingested via the Reader and
Indexer roles. Every Pro practitioner's Specialist and Checker calls read
from this same corpus — there is one library, not one per practitioner.
Practitioners never write to it; only the admin portal does.

## Vault — `data/vaults/<practitioner_id>.db` (Pro only)

```sql
clients (
  id TEXT PRIMARY KEY, name, email, password_hash, dob, country,
  created_at
)

questionnaire_responses (
  id TEXT PRIMARY KEY, client_id, questionnaire_id, questionnaire_version,
  answers_json, submitted_at
)

uploaded_files (
  id TEXT PRIMARY KEY, client_id, original_name, media_type,
  storage_path, uploaded_at
)  -- bytes live under data/vault-files/<practitioner_id>/, same
   -- id-not-filename convention as v1's originals store

wearable_connections (
  id TEXT PRIMARY KEY, client_id, provider,   -- oura | whoop | garmin
  status, connected_at
)

wearable_data_points (
  id TEXT PRIMARY KEY, client_id, provider, metric, value, recorded_at
)  -- v2: populated with fixture/dummy data on connect, not a live vendor
   -- pull. See 06-client-portal.md.

record_entries (
  id TEXT PRIMARY KEY, client_id, kind, content, created_at
)  -- kind ∈ lab | history | note | session_summary — same shape as v1

sessions (
  id TEXT PRIMARY KEY, client_id, title, started_at,
  status TEXT NOT NULL DEFAULT 'in_progress'  -- v2.7: in_progress | done
)

session_turns (
  id TEXT PRIMARY KEY, session_id, ordinal, question, answer, payload,
  created_at
)

-- v2.7: one clinician note + one client report per session, each with its
-- own draft/final state — separate documents, not two views of one text.
session_documents (
  id TEXT PRIMARY KEY, session_id, client_id,
  kind TEXT NOT NULL,          -- clinician_note | client_report
  status TEXT NOT NULL DEFAULT 'draft',   -- draft | final
  content TEXT NOT NULL DEFAULT '', updated_at,
  UNIQUE(session_id, kind)
)

-- v2.7: a clinician's freeform note per questionnaire theme for a client —
-- separate from the client's own answers, one row per (client, theme).
intake_notes (
  client_id, theme, note TEXT NOT NULL DEFAULT '', updated_at,
  PRIMARY KEY (client_id, theme)
)

-- v2.7: a practitioner's own personal weight for a shared library source.
-- Never touches the admin-set grade on the Neo4j Source node, and invisible
-- to every other practitioner and to admin — it only re-scores the source
-- list this practitioner's own POST /api/me/consult sees before the
-- Librarian chooses from it.
source_weights (
  source_id TEXT PRIMARY KEY, weight INTEGER NOT NULL, updated_at
)

audit_events (
  id TEXT PRIMARY KEY, ts, actor, action, detail, client_id
)  -- anything naming a client or quoting a clinical question goes here,
   -- never in core.db. Same rule as v1, same reason.
```

This is v1's patient vault schema (`patients` → `clients`, everything else
carried forward) instantiated once per Pro practitioner instead of once
globally. Erasure (`DELETE` a client) follows v1's redact-not-delete-audit
behavior unchanged.

## Filesystem

```
data/
  core.db
  originals/                 # library source files, unchanged from v1
  vaults/<practitioner_id>.db
  vault-files/<practitioner_id>/<file_id><ext>
```

## Cross-tenant reads the admin portal needs

Two numbers the admin dashboard shows — "how many clients does practitioner
X have" and site-wide client counts — require opening each vault rather than
one query, since vaults are deliberately not one queryable store. At 10-20
practitioners this is a fan-out of 10-20 cheap `SELECT count(*)` calls, not a
performance problem; if that changes, the fix is a periodic count rolled up
into `core.db`, not a shared clients table. Not built until it's needed.
