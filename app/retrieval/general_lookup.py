"""General lookup: the pgvector-backed fast RAG path — one Postgres
vector query, no graph traversal, no Neo4j round-trip at all. Sits
alongside app/retrieval/traversal.py's "deep research" path, not in
place of it; a practitioner picks per-question which they want
(app/main.py's MeConsult.retrieval_mode). See
app/retrieval/pgvector_store.py's module docstring for how chunks get
there (mirrored at ingest time, not looked up from Neo4j).
"""
from __future__ import annotations

from ..clients.llm_client import Role, get_client
from ..config import get_config
from ..patient.context import PatientContext
from .pgvector_store import search
from .traversal import TraversalResult

cfg = get_config()


def lookup(question: str, patient: PatientContext, min_grade: int,
          top_k: int | None = None) -> TraversalResult:
    """Embeds the question directly — no query-forming LLM call first.

    That's a deliberate speed/thoroughness tradeoff, not an oversight:
    specs/v6.2/01 found real seed-quality cost to skipping that step for
    the *deep-research* path's own seed search (44-53% result overlap
    against the LLM-formed query). General lookup is explicitly the
    fast, less-thorough option a practitioner opts into instead of deep
    research, so paying for that call here would defeat the point of
    offering this mode at all.

    Returns a TraversalResult (depth_reached=0, stopped_reason=
    "general_lookup", empty path_log) so every downstream consumer —
    app/reasoning/reasoner.py's answer(), and app/main.py's consult
    stream/result construction — handles this mode with no branching of
    their own; they already only care about `.accumulated`/`.usage`,
    not which retrieval strategy produced them. Records are plain dicts
    shaped like a Neo4j Chunk record (`text`/`document_title`/`grade`/
    `page_start`/`page_end`), so `store.is_chunk()` and `_locator()` see
    a normal chunk — they're duck-typed on the dict shape, not the source.
    """
    query_text = f"{patient.as_query_text()}\n\nQuestion: {question}"
    embedding = get_client(Role.EMBEDDER).embed([query_text])[0]
    rows = search(embedding, top_k=top_k or cfg.traversal_seed_top_k, min_grade=min_grade)
    accumulated = [
        {
            "id": r["id"], "text": r["text"], "document_title": r["document_title"],
            "document_id": r["document_id"], "grade": r["grade"],
            "page_start": r["page_start"], "page_end": r["page_end"],
        }
        for r in rows
    ]
    return TraversalResult(
        accumulated=accumulated, path_log=[], depth_reached=0,
        stopped_reason="general_lookup", usage={"input_tokens": 0, "output_tokens": 0},
    )
