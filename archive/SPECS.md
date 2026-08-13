# GraphRAG PoC — Specifications

**Goal:** A proof-of-concept Retrieval-Augmented Generation system using **traversal-based graph retrieval** over the *DUTCH Treatment Guide* PDF. It must (1) ingest a document, (2) answer questions, (3) **return the sources** backing each answer, and (4) assemble the *whole* connected context — not just top-k isolated chunks.

---

## 1. The core design question: graph DB vs vector DB

The user asked which is best. Short answer for **traversal graph retrieval**: **a graph database with a built-in vector index — Neo4j.** Reasoning:

| Approach | Semantic seed | Multi-hop / "whole context" | Verdict |
|---|---|---|---|
| Pure vector DB (Chroma, Qdrant) | ✅ excellent | ❌ none — returns k isolated chunks, no relationships | Not enough for the stated goal |
| Pure graph DB (no vectors) | ❌ needs exact keyword match to enter the graph | ✅ excellent | Hard to seed from a natural-language question |
| **Neo4j + native vector index (hybrid)** | ✅ via vector index | ✅ via Cypher traversal | **Chosen** |

**Why traversal wins for "whole context":** a plain vector search returns the *k* passages most similar to the question. If the answer spans several linked facts (e.g. a protocol that references a hormone that references a dosing rule), the linking passages may not individually rank in the top-k and are lost. GraphRAG instead (a) finds *entry-point* nodes by vector similarity, then (b) **walks the graph edges** to pull in every entity/passage connected to those entry points, reconstructing the full neighborhood before answering. Neo4j's native HNSW vector index lets us do the semantic seed and the traversal in one database, one query language (Cypher).

**Decision: Neo4j 5.x (Community) with native vector index.** Runs locally, free, Java 17 already present. No Docker needed.

---

## 2. Graph model

```
(:Document {id, filename, path})
   │  HAS_CHUNK
   ▼
(:Chunk {id, text, page, ordinal, embedding[]})  ── NEXT ──▶ (:Chunk ...)   (reading order)
   │  MENTIONS
   ▼
(:Entity {id, name, type, description, embedding[]})
   │
   └── (:Entity) ─[:RELATED {type, description, source_chunk_ids[]}]→ (:Entity)
```

- **Document** — one per ingested PDF.
- **Chunk** — a passage (~800 tokens, ~100 overlap). Carries `page` for citation and its own embedding. `NEXT` preserves reading order so we can widen context to neighbors.
- **Entity** — a concept/thing extracted by the LLM (e.g. a hormone, a symptom, a protocol). Has a description and its own embedding.
- **RELATED** — a typed, described relationship between two entities, each tagged with the `source_chunk_ids` it was extracted from (this is what makes **sources** traceable at the fact level).

Two vector indexes: one on `Chunk.embedding`, one on `Entity.embedding`.

---

## 3. Ingestion pipeline

```
PDF ─▶ extract text + page numbers (pypdf)
    ─▶ chunk (token-based, overlap)
    ─▶ for each chunk: LLM extracts { entities[], relationships[] }
    ─▶ embed chunks AND entities
    ─▶ MERGE into Neo4j (dedupe entities by normalized name)
    ─▶ build NEXT edges + vector indexes
```

- **Entity/relationship extraction** is the quality-critical LLM step. It reads a chunk and returns structured JSON: entities (name, type, description) and relationships (source, target, type, description). Deduplication merges entities with the same normalized name across chunks — this is what stitches the graph together across the whole document.
- Idempotent: re-ingesting the same file `MERGE`s rather than duplicates.

## 4. Query / retrieval pipeline (the traversal)

```
question
  ─▶ embed question
  ─▶ SEED: vector search → top-N Chunks + top-M Entities   (entry points)
  ─▶ TRAVERSE (Cypher): from seed entities, walk RELATED edges up to K hops;
                        from seed chunks, pull MENTIONS entities + NEXT neighbors
  ─▶ ASSEMBLE context: unique chunks + entity descriptions + the relationship
                        sentences connecting them, ordered & de-duplicated
  ─▶ LLM answers using ONLY that context, and must cite chunk ids
  ─▶ return { answer, sources[] }  where each source = {filename, page, chunk text snippet}
```

- `K` (hop depth), `N`, `M` are configurable; PoC defaults K=1–2, N=8, M=10.
- **Sources** are returned as a structured list: filename + page number + the exact chunk snippet used, so the answer is auditable.

## 5. Backend

- **FastAPI** (Python). Endpoints:
  - `POST /ingest` — multipart PDF upload → runs pipeline → returns counts (chunks, entities, relationships).
  - `POST /query` — `{question}` → `{answer, sources[], graph_context}`.
  - `GET /health` — Neo4j + LLM reachability.
  - `GET /stats` — node/edge counts for the loaded graph.
- Neo4j driver: official `neo4j` Python package.

## 6. Frontend

Single self-contained page (vanilla HTML/JS, no build step for the PoC):
- **Ingest panel**: pick PDF, upload, show progress + resulting counts.
- **Query panel**: ask a question, show the answer.
- **Sources panel**: list each source (filename · page · snippet), expandable.
- Optional: a small text list of the traversed entities/relationships so the "graph context" is visible.

## 7. LLM & embeddings provider (DECIDED)

**Chosen: Claude API for extraction + answers, Ollama `nomic-embed-text` for embeddings (local, free).**
- Extraction/answers: `claude-opus-4-8` for extraction quality (can drop to Haiku 4.5 for cost during iteration).
- Embeddings: Ollama `nomic-embed-text` (768-dim), pulled locally — no embedding API key needed.
- Auth: user will set `ANTHROPIC_API_KEY` (or `ant auth login`). Both are natively supported by `neo4j-graphrag-python`.

## 7a. Algorithm & implementation research (journals + web, July 2026)

The landscape has several traversal-based GraphRAG families. Summary of what fits a **single medical document, "whole context", auditable sources** PoC:

| Approach | Traversal mechanism | Fit for this PoC |
|---|---|---|
| **Microsoft GraphRAG** | Leiden community detection + hierarchical community summaries; local + global search | Powerful for corpus-wide themes, but heavy indexing and many LLM calls; overkill for one doc. |
| **HippoRAG / HippoRAG 2** (NeurIPS'24 / 2025) | **Personalized PageRank** propagating from query-seed nodes across an open KG; "neurobiologically inspired". 10–30× cheaper multi-hop. | Excellent multi-hop "whole context"; PPR is the standout traversal idea. Adopt as an optional re-rank layer. |
| **LightRAG** (EMNLP'25) | Dual-level retrieval: low-level (entities+relations) + high-level (themes); incremental, few LLM calls | Efficient, good comprehensiveness; a strong alternative to MS GraphRAG. |
| **PathRAG** | Flow-based path pruning between seed nodes (−44% context, same accuracy) | Useful for trimming; not needed at PoC scale. |
| **Neo4j `neo4j-graphrag-python`** (official) | `VectorCypherRetriever`: vector seed → explicit **K-hop Cypher traversal**; `SimpleKGPipeline` for extraction/ingest | **Primary implementation** — transparent, easy to expose sources, supports Claude + Ollama natively. |

**Design decision:**
- **Primary retriever = `VectorCypherRetriever`** (deterministic K-hop traversal). Transparent and directly citable — best for a demonstrable PoC.
- **Optional stretch = Personalized PageRank re-ranking** (the HippoRAG idea) via Neo4j GDS, to show the multi-hop "whole context" advantage over plain vector top-k.
- **Ingestion via `SimpleKGPipeline`** (chunk → LLM entity/relation extraction → embed → write), which matches our Section 3 pipeline and avoids hand-rolling driver code.

**Key sources:**
- Neo4j GraphRAG for Python — https://neo4j.com/docs/neo4j-graphrag-python/current/ · https://github.com/neo4j/neo4j-graphrag-python
- HippoRAG (NeurIPS'24) — https://arxiv.org/pdf/2405.14831 · HippoRAG 2 / "From RAG to Memory" — https://arxiv.org/pdf/2502.14802 · https://github.com/OSU-NLP-Group/HippoRAG
- LightRAG (EMNLP'25) — https://arxiv.org/html/2410.05779v1 · https://github.com/HKUDS/LightRAG
- Integrating Microsoft GraphRAG into Neo4j — https://neo4j.com/blog/developer/microsoft-graphrag-neo4j/
- Architecture comparison — https://medium.com/graph-praxis/graphrag-vs-hipporag-vs-pathrag-vs-og-rag-choosing-the-right-architecture-for-your-knowledge-graph-a4745e8b125f

## 8. Success criteria (PoC "done")

1. `POST /ingest` on the DUTCH PDF completes and reports > 0 entities and > 0 relationships.
2. A domain question (e.g. "What does an elevated cortisol pattern indicate and how is it treated?") returns a coherent answer **plus** a sources list with correct page numbers.
3. The answer draws on chunks connected via traversal that a plain top-k vector search alone would miss (demonstrable by comparing graph context vs. raw vector hits).
4. Frontend can drive both ingest and query end-to-end in a browser.

## 9. Explicit non-goals (PoC scope discipline)

- No auth, no multi-user, no persistence beyond Neo4j.
- No incremental/streaming ingest UI beyond a simple progress indicator.
- No production hardening (rate limits, retries beyond basic, observability).
- Single document at a time is fine (schema supports multiple, but we test with one).
