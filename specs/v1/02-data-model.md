# 02 · Data model

Two stores, deliberately separate. The split is the deck's "patient data stays in
its own vault" claim, made structural rather than promised.

| Store | Holds | Why here |
|---|---|---|
| **Neo4j** | Sources, passages, topics, concepts, library audit | A connected corpus; traversal is the retrieval mechanism |
| **SQLite** | Patients, record entries, consultations, patient audit | Small, per-patient, and must not leave the vault |
| **Filesystem** | The uploaded file, byte-for-byte | Bytes do not belong in a graph; the original must survive extraction |

Nothing in Neo4j names a patient, quotes a clinical question, or carries a patient
id. This is enforced by a check in `verify.py` that fails when the boundary is
crossed — it was added because the boundary *was* crossed once (see
[07](07-security.md#the-leak-that-was-found)).

---

## Neo4j — the knowledge library

```
(:Source {
    id, title, filename, kind, origin, grade, summary, created_at,
    content_hash, body, author, published, reference,
    page_count, char_count, passage_count,
    original_name, original_media_type, original_bytes
 })
   │
   ├─[:HAS_CHUNK]──▶ (:Chunk { id, text, ordinal, page_start, page_end })
   │                    │
   │                    ├─[:NEXT]──────▶ (:Chunk)      reading order
   │                    └─[:MENTIONS]──▶ (:Concept { name })
   │
   └─[:TAGGED]────▶ (:Topic { name })

(:AuditEvent { id, ts, actor, action, detail })    library events only
```

### Nodes

**`:Source`** — one ingested document.

| Field | Notes |
|---|---|
| `grade` | 1–10 reliability. The Reader proposes; the admin decides. The single most important field: it gates what the assistant may use. |
| `content_hash` | SHA-256 of the whitespace-normalised body. Uniqueness-constrained, so a re-upload is refused rather than duplicated. |
| `body` | The original text as ingested. Stored because concatenating passages back together would double the overlap regions, and because the deck promises the original stays readable. |
| `author`, `published`, `reference` | Extracted by the Reader **only if stated in the text**. Empty rather than inferred — a fabricated citation is worse than a blank one, because a clinician may try to look it up. |
| `kind`, `origin` | Admin-supplied. Shown beside every citation. |
| `original_name`, `original_media_type`, `original_bytes` | The uploaded file as it arrived. `null` for pasted text, which has no original. See below. |

**`:Chunk`** — a passage; the unit that is quoted and cited.

| Field | Notes |
|---|---|
| `ordinal` | 0-based position within the source. |
| `page_start`, `page_end` | Both set for PDFs; `null` for unpaginated text. A passage straddling a page break records both, so a citation can say "pages 3–4". |

**`:Topic`** — a browsing shelf, 1–4 per source. LLM-chosen but converging: the
Reader is shown the topics already in use and reuses one where it fits.

**`:Concept`** — what a passage is *about*, 3–8 per passage. These are the edges
that make the library a corpus rather than a pile of documents.

### Relationships

| Edge | Meaning |
|---|---|
| `HAS_CHUNK` | Source → its passages |
| `NEXT` | Passage → the next passage in reading order |
| `MENTIONS` | Passage → a concept it is about |
| `TAGGED` | Source → a topic |

### Constraints

```cypher
CREATE CONSTRAINT source_id     FOR (n:Source)  REQUIRE n.id IS UNIQUE
CREATE CONSTRAINT chunk_id      FOR (n:Chunk)   REQUIRE n.id IS UNIQUE
CREATE CONSTRAINT topic_name    FOR (n:Topic)   REQUIRE n.name IS UNIQUE
CREATE CONSTRAINT concept_name  FOR (n:Concept) REQUIRE n.name IS UNIQUE
CREATE CONSTRAINT source_hash   FOR (n:Source)  REQUIRE n.content_hash IS UNIQUE
```

`source_hash` is the one that matters: the read-then-write duplicate check could be
passed by two concurrent uploads, so the database is the final arbiter.

### Cypher note — `FOREACH`, not `UNWIND`

Writes inside `ingest_source` use `FOREACH` over the topic and passage lists.
`UNWIND` over an **empty** list yields zero rows and silently discards the rest of
the query pipeline — an untagged source was written with **no passages at all**.
`FOREACH` tolerates the empty case. `verify.py` carries a regression test for this.

---

## Filesystem — the original file store

Directory at `ORIGINALS_PATH` (`data/originals`, `/opt/clinic/data/originals` in
production). One file per source, named `<source_id><ext>` — the id, not the
uploaded filename, so two uploads called `guidelines.pdf` cannot collide and a
filename from the wire never becomes a path.

**Why it exists.** Ingestion is lossy in ways that are invisible afterwards. Chunking
splits the text and overlaps the seams; PDF extraction discards tables, figures,
layout and anything in a scanned page; `body` is only what `pypdf` could read. A
clinician who distrusts a citation needs the document, not our reading of it. Storing
the bytes also means a future extractor — better PDF handling, OCR for scanned pages —
can re-ingest from the original instead of asking for the upload again.

This is **additive**: chunking, `body` and every retrieval path are unchanged. The
original is for humans to open, never for retrieval, and is never sent to a model.

**Lifecycle.**
- Written **after** the Neo4j write commits, so a duplicate rejected by the
  `source_hash` constraint leaves no orphan file.
- A failed write is logged and the ingest still succeeds — losing a whole source
  because its archive copy could not be saved is the worse outcome. The source then
  behaves exactly like a pre-existing one (no original; see migration below).
- Deleted by `delete_source`, which is also what supersede-by-`replaces` calls, so an
  orphan file cannot outlive its node. Deletion is best-effort: a missing file is not
  an error.

**Pasted text has no original.** `original_name` is `null` and the download endpoint
404s — the passages and `body` *are* the source, and inventing a `.txt` file to
download would imply an artefact the practitioner never supplied.

---

## SQLite — the patient vault

File at `SQLITE_PATH` (`/opt/clinic/data/patients.db` in production).

```sql
patients (
  id TEXT PRIMARY KEY, name, country, dob, created_at
)

record_entries (
  id TEXT PRIMARY KEY, patient_id, kind, content, created_at
)
-- kind ∈ lab | history | note | session_summary

sessions (
  id TEXT PRIMARY KEY, patient_id, title, started_at
)

session_turns (
  id TEXT PRIMARY KEY, session_id, ordinal,
  question, answer, payload, created_at
)
-- payload: the full JSON consult result minus the answer, so a saved
-- consultation replays with its citations, verdict and traversal intact

audit_events (
  id TEXT PRIMARY KEY, ts, actor, action, detail, patient_id
)
-- anything naming a patient or quoting a clinical question
```

### Why sessions live here

A consultation is clinical detail about a patient — the questions asked as much as
the answers given. Holding them server-side also means a follow-up resolves against
history read from the vault rather than history supplied by the client.

### Erasure

`delete_patient` removes the patient, their entries, their sessions and turns, then
**redacts** the detail of their audit rows to `[redacted on erasure]` while keeping
the rows themselves, and appends a `patient erased` event. An erasure request
should not also erase the evidence that it was honoured.

---

## Concept canonicalisation

A concept edge exists only if two passages produce the **same string**, so one idea
must yield one label. Two mechanisms, in `app/knowledge.py`:

1. **A deterministic alias table** (`ALIASES`), applied when indexing *and* when
   reading a question, so both sides meet:
   `Fe`, `ferrous`, `serum iron`, `iron stores` → `iron`;
   `25(OH)D`, `cholecalciferol`, `vitamin D3` → `vitamin d`;
   `HT`, `Hashimoto's thyroiditis` → `hashimoto thyroiditis`;
   `HRT` → `hormone replacement therapy`.
2. **An LLM consolidation pass** (`POST /api/consolidate`) for the tail no static
   map anticipates. It is instructed to merge only identical ideas — abbreviations,
   synonyms, spelling and plural variants — and explicitly *not* to merge related
   or hierarchical terms. Observed behaviour: it merged `cholecalciferol → vitamin d`
   and refused to merge `ferritin` with `iron`.

`canon()` also lowercases, strips punctuation and possessives, and singularises —
with a guard list for clinical nouns whose trailing *s* belongs to the word
(`thyroiditis`, `diabetes`, `analysis`). Without that guard `hashimoto thyroiditis`
became `hashimoto thyroiditi`, silently splitting the concept in two.

## Migration behaviour

Both schemas are created idempotently at startup and only ever added to. Sources
ingested before a field existed keep working:

- no `body` → the reader reassembles the text from its passages and says so
- no concepts → the source is an island, listed by `GET /api/graph` as unlinked and
  fixable with `POST /api/relink`
- no `original_name` → no original was kept (pasted text, or ingested before the file
  store existed). The download control is not offered and the endpoint 404s. Existing
  sources are **not** backfilled: the bytes were never held, so there is nothing to
  backfill from.
