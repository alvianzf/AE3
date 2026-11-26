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
from .seed_search import form_search_query
from .traversal import TraversalResult

cfg = get_config()


def lookup(question: str, patient: PatientContext, min_grade: int,
          top_k: int | None = None,
          accessible_private_ids: set[str] | None = None,
          folder: str = "", topic: str = "") -> TraversalResult:
    """One Postgres vector query, no graph traversal/hop-judging at all —
    that part of the speed tradeoff against deep_research stays.

    Found live, 2026-11-27: a short/vague question ("data for athletes")
    embedded directly returned ten chunks from completely unrelated
    documents (a pathophysiology textbook, a women's health title) — not
    merely "less thorough" than deep research, but actively useless,
    because a 3-4 word query has little to lock onto in embedding space
    on its own. Deep research's seed stage already pays for exactly one
    cheap Role.ANSWER_ENGINE call (seed_search.form_search_query()) to
    turn a vague question into a real search phrase before embedding it
    — general_lookup now pays that same single cheap call too, rather
    than skipping query formation entirely. Still meaningfully faster
    than deep_research (no multi-hop traversal, no per-hop judging calls,
    which is where deep_research actually spends most of its time), just
    no longer embeds a bare 3-word question and calls that "search."

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
    search_query, query_usage = form_search_query(question, patient)
    query_text = f"{patient.as_query_text()}\n\nQuestion: {search_query}"
    embedding = get_client(Role.EMBEDDER).embed([query_text])[0]
    rows = search(embedding, top_k=top_k or cfg.traversal_seed_top_k, min_grade=min_grade,
                 accessible_private_ids=accessible_private_ids, folder=folder, topic=topic)
    accumulated = [
        {
            "id": r["id"], "text": r["text"], "document_title": r["document_title"],
            "document_id": r["document_id"], "grade": r["grade"],
            "page_start": r["page_start"], "page_end": r["page_end"],
        }
        for r in rows
    ]
    # Grade no longer filters these results (pgvector_store.search()) —
    # it orders them instead, so a higher-trust source lists (and gets
    # cited) ahead of a lower-trust one for the same question, same
    # reasoning as GraphTraversalRetriever's own sort.
    accumulated.sort(key=lambda c: c["grade"], reverse=True)
    return TraversalResult(
        accumulated=accumulated, path_log=[], depth_reached=0,
        stopped_reason="general_lookup", usage=query_usage,
    )
