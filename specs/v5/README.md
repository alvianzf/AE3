# v5 — Graph-traversal retrieval: replacing catalogue-based RAG

**Status: implemented, not live-verified** (same caveat as
[v4.2](../v4.2/README.md): every module imports cleanly, `app/main.py`'s
whole module body executes without error, and `tests/test_traversal.py`'s
5 stopping/pruning tests pass deterministically against a mocked LLM —
but nothing here has run against a real Neo4j instance, a real Nebius
endpoint, or a downloaded HHEM model).

Replaces `app/knowledge.py` and `app/llm.py` entirely — retrieval is no
longer "the Librarian picks source cards, then traversal fills a budget
from concept links." It's now: seed search (vector + full-text) finds
starting points, then a `GraphTraversalRetriever` expands outward one hop
at a time, an LLM judges each newly-discovered node's relevance against
the original question *and the specific patient asking it*, and a branch
dies the moment it goes cold rather than continuing on a fixed budget.

## New package layout

- `app/clients/llm_client.py` — one `LLMClient` per AI-team role
  (base_url/model/api_key independently configurable per role, never
  hardcoded — see `app/config.py`'s `<ROLE>_BASE_URL`/`<ROLE>_API_KEY`
  vars).
- `app/graph/` — `driver.py` (the shared Neo4j connection), `schema.py`
  (constraints + vector + full-text indexes), `store.py` (the
  Document/Chunk/Entity graph: ingestion writes, the full admin-surface
  API — list/search/paginate, coverage, audit, merge-dedup — and the
  retrieval-support queries traversal actually calls).
- `app/patient/context.py` — `get_patient_context()`: the patient data
  that shapes retrieval, not just gets appended at the end. See
  [01](01-patient-context-adaptation.md) for why this reads the existing
  SQLite vault instead of MySQL.
- `app/ingestion/pipeline.py` — Reader → chunk → Embedder → KG-builder →
  `store.ingest_document()`, idempotent on content hash.
- `app/retrieval/` — `seed_search.py` (patient-conditioned search query
  formation + vector/full-text seeding) and `traversal.py`
  (`GraphTraversalRetriever`, the actual hop-by-hop pruning loop).
- `app/reasoning/` — `reasoner.py` (the final KIMI-K3 answer, once per
  query) and `checker.py` (the anti-hallucination pass, carried forward
  from [v4.2](../v4.2/README.md) — see [02](02-scope-decisions.md)).
- `tests/test_traversal.py` — the stopping/pruning logic, verified
  independent of any real LLM (a plain Python `judge_fn` is injected).

## Docs

- [**01 · Patient context: adapting to the existing SQLite vault**](01-patient-context-adaptation.md) —
  the brief assumed MySQL; this repo has none. What `get_patient_context()`
  actually reads, and the two real data-quality gaps that come with that.
- [**02 · Scope decisions carried over from the existing product**](02-scope-decisions.md) —
  grading (`Document.grade`, carried forward) and the anti-hallucination
  Checker (carried forward) — both decided explicitly, not defaulted into
  silently, because both are marketed, load-bearing safety features of
  the shipped product.
- [**03 · Known gaps and follow-up work**](03-known-gaps.md) — the
  Embedder's write-path-only status, the consult UI's `t.librarian`
  display block that will silently show nothing now, `history` folded
  into the question text as a stopgap, and the APOC dependency in
  `store.merge_entities()`.
