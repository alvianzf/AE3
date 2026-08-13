# Online Clinic Platform — Phase 1 POC

> **Amendment (after approval): all-Anthropic, no Ollama.**
> The plan below specifies Ollama `nomic-embed-text` as the Indexer and Neo4j
> vector search for retrieval. On request, the stack is now Anthropic-only.
> Anthropic has no embeddings API, so **embeddings and vector search were removed
> entirely** and replaced with card-based retrieval: the Librarian reads the
> catalogue of source cards at or above the grade bar and picks which sources to
> open. The `Indexer` role, the `chunk_embeddings` vector index, `MIN_SCORE`, and
> the `ollama` dependency are all gone. Everything else below stands.
> See README.md § "How retrieval works" for the tradeoff this accepts.

## Context

`online-clinic-platform-schema_1.pdf` proposes a digital clinic for hormonal health whose differentiator is a **source-grounded AI assistant**: practitioners ask questions during a consultation and get answers drawn only from (1) the clinic's own curated, graded knowledge library, (2) the patient's record, and (3) live PubMed. Answers cite their sources, an optional independent checker verifies them, and a session summary is written back to the patient record.

This POC exists to **prove the loop works end to end in a browser** for an investor demo. PubMed is explicitly out of scope, so the assistant answers from two sources: clinic knowledge + patient file. The frontend is deliberately thin — it exists to make the pipeline visible, not to be a product.

The repo currently holds a *different* project: a GraphRAG PoC over a DUTCH hormone PDF (`SPECS.md`, `PLAN.md`, `app/config.py`, `app/graph.py` — Phase 0–1 only). We keep its infrastructure choices (FastAPI + Neo4j + Ollama embeddings + Anthropic) and its `config.py`, and replace the graph-extraction pipeline with the clinic ingestion pipeline.

### Decisions taken (from clarifying questions)

| Area | Decision |
|---|---|
| Storage | **Neo4j** for the knowledge library, **SQLite** for patient records — physically separate, mirroring the deck's "patient data stays in its own vault" |
| Portals | **Both, thin**: Admin (upload → ingest → source cards → coverage → audit log) and Practitioner (patients → file → chat → save summary) |
| AI pieces | All four: grade filter, anti-hallucination check, session-summary write-back, separate models per role |
| Seed data | **None** — everything is created live through the UI, so the POC includes patient creation |

### Assumptions I'm making explicit

1. **No entity/relationship graph.** The deck describes "index by meaning" = embeddings, not a knowledge graph. Neo4j earns its place here as source/chunk/topic store + native vector index (the coverage dashboard becomes a one-line Cypher query). `SimpleKGPipeline`, `ENTITIES`, `RELATIONS`, `PATTERNS` in `app/graph.py` are dropped.
2. **Patient context is not retrieved, it's included whole.** A POC patient file is a few hundred words; embedding it would add machinery and lose recall. Every consult passes the full patient file to the Specialist.
3. **No auth, no country-vault enforcement.** Country is a field on the patient (SK/PL) shown in the UI; it does not route storage.
4. **`ANTHROPIC_API_KEY` in `.env` is still the `sk-ant-...` placeholder** — a real key is required before anything runs.

---

## The AI team (four models, one per role)

| Role | Model | Job |
|---|---|---|
| Reader | `claude-haiku-4-5` | Reads an uploaded source → `{title, summary, topics[], suggested_grade}` (structured output) |
| Indexer | Ollama `nomic-embed-text` (768-d) | Embeds every chunk |
| Librarian | `claude-haiku-4-5` | Question + patient file → 1–3 search queries (structured output). Does not answer. |
| Specialist | `claude-opus-5` | Writes the grounded answer citing `[S1]`, `[S2]` … |
| Checker | `claude-haiku-4-5` | Verifies each claim against the retrieved passages → `{verdict, unsupported[]}` (structured output) |

API notes that matter (verified against the `claude-api` skill):
- **`anthropic==0.49.0` in the venv is too old** — it predates `output_config`/structured outputs. Upgrade to the latest `anthropic` in `requirements.txt`.
- Specialist: `thinking={"type": "adaptive"}` (Opus 5's default), `output_config={"effort": "medium"}`, `max_tokens=8000`. Do **not** pass `thinking={"type":"disabled"}` — on Opus 5 that can leak `<thinking>` tags into the visible answer.
- Haiku 4.5 does **not** support `output_config.effort` (it errors). Use `output_config={"format": {...}}` only.
- No `temperature` / `top_p` on Opus 5 — they 400.

---

## Data model

**Neo4j (knowledge)**
```
(:Source {id, title, filename, kind, origin, grade, summary, created_at})
   -[:HAS_CHUNK]-> (:Chunk {id, text, ordinal, page, embedding})
   -[:TAGGED]->    (:Topic {name})
(:AuditEvent {id, ts, actor, action, detail})
```
Vector index `chunk_embeddings` on `Chunk.embedding`, 768-d cosine (the `create_vector_index` call already in `app/graph.py:83` is reused as-is).

**SQLite (patients)** — file `data/patients.db`
```sql
patients(id TEXT PK, name, country, dob, created_at)
record_entries(id TEXT PK, patient_id, kind, content, created_at)
  -- kind ∈ lab | history | note | session_summary
```

---

## Files

| File | Action |
|---|---|
| `app/config.py` | **Extend** — add `reader_model`/`librarian_model`/`answer_model`/`checker_model`, `sqlite_path`, `min_grade` default, `chunk_size`/`chunk_overlap`. Keep the existing Neo4j/Ollama/index-name fields verbatim. |
| `app/graph.py` | **Rewrite** — keep `get_driver()`, `get_embedder()`, `ensure_indexes()`. Delete `ENTITIES`/`RELATIONS`/`PATTERNS`/`build_pipeline()`/`LEXICAL`/`get_llm()`. Rename to `app/knowledge.py`; add `ingest_source()`, `search()` (grade-filtered vector query), `list_sources()`, `set_grade()`, `delete_source()`, `coverage()`, `log()`/`audit()`. |
| `app/llm.py` | **New** — one Anthropic client; `read_source()`, `plan_queries()`, `answer()`, `check()`, `summarize_session()`. Each role is one function with its model pinned. |
| `app/patients.py` | **New** — SQLite connection + schema bootstrap + `create_patient()`, `list_patients()`, `get_patient()` (patient + all entries), `add_entry()`, `patient_file_text()` (flattens the record for the prompt). |
| `app/main.py` | **New** — FastAPI app, routes below, `StaticFiles` mount for `static/`. |
| `static/index.html`, `static/app.js`, `static/style.css` | **New** — two-tab vanilla-JS page, no build step. |
| `requirements.txt` | Upgrade `anthropic`; drop `neo4j-graphrag` if `create_vector_index` is reimplemented as raw Cypher (decide during Phase 1 — keeping it is fine). |
| `.env.example` / `.env` | Add the four model vars + `SQLITE_PATH` + `MIN_GRADE`. |
| `SPECS.md`, `PLAN.md` | Superseded by this plan — replace or archive; do not leave stale DUTCH-GraphRAG docs alongside clinic code. |

---

## Retrieval (the core loop)

```
question + patient_id + min_grade
  → Librarian(Haiku): {queries: [1-3 strings]}
  → for each query: embed (Ollama) → db.index.vector.queryNodes('chunk_embeddings', k*3, $vec)
                    → WHERE source.grade >= min_grade → take top k
  → merge + dedupe by chunk id → passages S1..Sn (each carries source title, grade, page)
  → Specialist(Opus 5): system = "answer ONLY from the passages and the patient file;
                                  cite [S1] style; say what you don't know"
  → Checker(Haiku): {verdict: pass|weak, unsupported: [claim...]}
  → return {answer, sources[], check, queries}
```

Over-fetch-then-filter (`k*3`) is needed because Neo4j's vector index has no pre-filter — this is the simplest correct approach at POC scale.

---

## Endpoints

**Admin**
- `POST /api/sources` — multipart: file (PDF/txt/md) *or* pasted text, plus `kind` and `origin`. Runs Reader → chunk → embed → write. Returns the source card.
- `GET /api/sources` — all source cards
- `PATCH /api/sources/{id}` — `{grade}` (admin override of the Reader's suggestion)
- `DELETE /api/sources/{id}` — removes source + its chunks (proves "correct or remove a source and both shelves update")
- `GET /api/coverage` — `[{topic, sources, chunks}]`
- `GET /api/audit` — the full log

**Practitioner**
- `POST /api/patients` — `{name, country, dob}`
- `GET /api/patients` / `GET /api/patients/{id}`
- `POST /api/patients/{id}/entries` — `{kind, content}`
- `POST /api/consult` — `{patient_id, question, min_grade, run_check}` → the retrieval loop above
- `POST /api/patients/{id}/summary` — `{transcript}` → Haiku summary → saved as a `session_summary` entry

**Ops**
- `GET /api/health` — Neo4j / Ollama / Anthropic reachability

---

## Frontend

One page, two tabs, no framework.

- **Admin** — upload form (file or textarea + kind + origin) with a spinner; source-card list showing title · origin · topics · grade slider (1–10) · delete; coverage table (topic → source count, chunk count); audit log panel.
- **Practitioner** — patient list + "new patient" form; selected patient shows record entries and an "add entry" form (lab / history / note); chat box with a **min-grade slider** and an **anti-hallucination toggle**; answer panel renders the answer with clickable `[S1]` markers, a sources list (title · grade · page · snippet), the checker badge (pass / weak + unsupported claims), and the Librarian's queries in a collapsed "how it searched" detail; a "Save session summary" button.

Making the grade slider, the checker badge, and the search queries visible on screen is what turns the deck's claims into something an investor can watch happen.

---

## Build order

1. **Config + storage layer** — `config.py` extension, `knowledge.py` (driver, index, schema constraints), `patients.py` (SQLite bootstrap). Checkpoint: `/api/health` green on all three.
2. **Ingestion** — `llm.read_source()` + chunk + embed + write + audit. Checkpoint: upload a text file via curl, see a source card and chunk count.
3. **Retrieval + answering** — Librarian → grade-filtered search → Specialist → Checker. Checkpoint: `/api/consult` returns a cited answer against an uploaded source.
4. **Patients** — CRUD + entries + summary write-back. Checkpoint: patient file text appears in the Specialist prompt and influences the answer.
5. **Frontend** — both tabs.
6. **Demo pass** — walk the full script below, fix rough edges.

---

## Verification

Automated where it's cheap, manual for the demo path.

1. `GET /api/health` returns all three green (catches the placeholder API key immediately).
2. **Ingestion** — `POST /api/sources` with a short text source returns a card with a non-empty `summary`, ≥1 topic, a grade in 1–10, and `chunks > 0`. `GET /api/coverage` shows the topic.
3. **Grade filter (the load-bearing test)** — ingest two sources answering the same question, one graded 9 and one graded 3. Query with `min_grade=7`; assert the grade-3 source appears in **neither** the sources list nor the answer. Lower to `min_grade=1` and assert it now appears. This is the one behavior a demo viewer will actually probe.
4. **Grounding** — ask a question with no supporting source; the answer should decline rather than invent, and `sources` should be empty.
5. **Checker** — verify it returns `pass` on a well-supported answer. To see it fire negatively, temporarily lower `min_grade` so thin passages get through, or hand-edit a draft claim in a scratch script.
6. **Patient influence** — add a lab entry ("ferritin 11 ng/mL"), ask a related question, confirm the answer references it. Save a session summary and confirm it appears as a `session_summary` entry and is present in the next consult's prompt.
7. **Deletion** — delete a source; confirm its chunks are gone (`/api/coverage` count drops) and it stops appearing in answers.
8. **Browser end-to-end** — run the demo script: create patient → add labs → upload two sources at different grades → ask a question → move the grade slider → see the source list change → save the summary.

Run the server with `.venv/bin/uvicorn app.main:app --reload` and open `http://localhost:8000`.

---

## Open risks

- **`anthropic` upgrade** — 0.49.0 is too old for structured outputs. If the upgrade conflicts with `neo4j-graphrag==1.18.0`'s pins, drop `neo4j-graphrag` (only `create_vector_index` is used; it's ~5 lines of Cypher) rather than pinning the SDK back.
- **Python 3.14** — the venv is 3.14.6. Verify the upgraded `anthropic` installs cleanly there before building on it.
- **Neo4j vector pre-filtering** — over-fetch-then-filter degrades if a demo library is dominated by low-grade sources. At POC scale (tens of sources) it's fine; noted so it isn't mistaken for a production pattern.
- **Scanned PDFs** — `pypdf` returns empty text for image-only PDFs. If that happens during the demo, the ingest response should say so plainly rather than writing a source with zero chunks. No OCR dependency will be added without asking.
