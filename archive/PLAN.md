# GraphRAG PoC — Implementation Plan

Stack locked: **Neo4j (Homebrew, local) + native vector index**, **`neo4j-graphrag-python`**, **Claude (`claude-opus-4-8`) for extraction/answers**, **Ollama `nomic-embed-text` for embeddings**, **FastAPI backend + vanilla-JS frontend**.

Primary retrieval = `VectorCypherRetriever` (vector seed → K-hop Cypher traversal). **Personalized PageRank re-rank (HippoRAG idea) is IN SCOPE** with a compare toggle. **Graph visualization of the traversed subgraph is IN SCOPE.**

**Locked decisions:** extraction model = **Opus 4.8**; extraction schema = **medical-guided** (Hormone, Metabolite, Symptom, Condition, Treatment, Biomarker, DosingRule, …); PageRank comparison = **yes**; frontend = **minimal page + subgraph visualization** (vis-network).

---

## Phase 0 — Environment setup (infra)
1. `brew install neo4j` (uses Java 17 already present); start it; set an initial password.
2. `ollama pull nomic-embed-text` (local embedding model, 768-dim).
3. Confirm `ANTHROPIC_API_KEY` is set (or `ant auth login`). Verify with a tiny Claude call.
4. Python venv (3.14) + deps: `neo4j-graphrag[anthropic,ollama]`, `fastapi`, `uvicorn`, `pypdf`, `python-multipart`.
   - **Risk note:** confirm `neo4j-graphrag-python` supports Python 3.14; if it pins <3.14, create the venv with an older Python via Homebrew. I'll verify at this step and report.

**Checkpoint:** `GET /health` will later confirm all three (Neo4j, Ollama, Claude) reachable.

## Phase 1 — Backend skeleton
5. `app/config.py` — env-driven config (Neo4j URI/user/pass, model names, K/N/M retrieval params).
6. `app/graph.py` — Neo4j driver + `SimpleKGPipeline` wiring (Claude extractor, Ollama embedder), schema (`Document/Chunk/Entity` + `RELATED`), vector index creation on `Chunk.embedding` and `Entity.embedding`.
7. `app/main.py` — FastAPI app with `GET /health`, `GET /stats`.

**Checkpoint:** server boots, `/health` green.

## Phase 2 — Ingestion
8. `POST /ingest` — accept PDF upload → extract text+page numbers (pypdf) → run `SimpleKGPipeline` (chunk → extract entities/relations → embed → write) → build `NEXT` chunk-order edges → return counts.
9. Ingest the DUTCH PDF; confirm `/stats` shows > 0 entities and > 0 relationships.

**Checkpoint:** graph populated; spot-check a few entities/relationships in Neo4j Browser.

## Phase 3 — Traversal retrieval + answering
10. `app/retriever.py` — `VectorCypherRetriever` with a Cypher traversal template: from vector-seed chunks/entities, pull `MENTIONS` entities, `RELATED` neighbors (K hops), and `NEXT` neighbors; return chunks + entity descriptions + connecting relationship sentences, de-duplicated, each carrying `{filename, page, chunk_id, snippet}`.
11. `POST /query` — embed question → retrieve traversed context → Claude answers **using only that context, citing chunk ids** → return `{answer, sources[], graph_context}`.

**Checkpoint:** success criteria #2 and #3 from SPECS — coherent answer + correct-page sources; graph context includes linked chunks a plain top-k would miss.

## Phase 4 — Frontend
12. `static/index.html` (+ inline JS/CSS, no build) — Ingest panel (upload + counts), Query panel (question + answer), Sources panel (filename · page · snippet, expandable), and a small traversed-entities/relationships list to make the "graph context" visible.
13. Serve statics from FastAPI.

**Checkpoint:** success criterion #4 — full ingest+query loop works in a browser.

## Phase 5 — Demo + optional stretch
14. Seed 3–4 example domain questions; capture a short run-through.
15. *(Optional)* Add Personalized PageRank re-rank via Neo4j GDS and a toggle to compare "vector-only" vs "graph-traversal" context side by side — concretely demonstrates the whole-context advantage.

---

## Deliverables
- `SPECS.md`, `PLAN.md` (this)
- `app/` (FastAPI backend), `static/` (frontend), `requirements.txt`, `.env.example`, `README.md` (run instructions)
- Populated Neo4j graph from the DUTCH PDF

## Open risks I'll surface as I go
- Python 3.14 compatibility of `neo4j-graphrag-python` (Phase 0).
- PDF extraction quality on the DUTCH guide (scanned vs. text PDF) — if it's image-only, we'd need OCR; I'll check at Phase 2 and report before adding OCR deps.
- Claude cost during full-document extraction — I'll default extraction to Haiku if the doc is large, and note it.
