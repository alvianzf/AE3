"""Seed search: question + patient context -> a search query -> seed chunks
+ seed entities for GraphTraversalRetriever to expand from.

Patient context shapes this from the start (the clinical-safety
requirement this whole design is built around) — the search query the
Answer Engine forms is conditioned on the patient's active conditions/
medications/labs, not just the raw question text, so a drug-interaction
question actually goes looking for interactions with what this patient is
already taking.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..clients.llm_client import Role, get_client
from ..config import get_config
from ..graph import store
from ..patient.context import PatientContext

cfg = get_config()

SEARCH_QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "search_query": {
            "type": "string",
            "description": "A search query text that would find passages "
                           "relevant to the question, given this patient's "
                           "specific conditions/medications/labs.",
        },
    },
    "required": ["search_query"],
    "additionalProperties": False,
}

SEARCH_QUERY_SYSTEM = (
    "You form a search query for a clinical knowledge base, given a "
    "practitioner's question and the specific patient it's about.\n\n"
    "Ground the query in this patient's actual conditions, medications, and "
    "labs, not just the question's words — a question about a new supplement "
    "for a patient already on a specific medication should search for that "
    "medication's interactions too, not just the supplement in isolation. "
    "This is what lets the search surface a contraindication the question "
    "itself never mentions."
)


@dataclass
class SeedResult:
    search_query: str
    seed_chunk_ids: list[str]
    seed_entity_ids: list[str]
    seed_records: dict[str, dict]  # id -> the record store.py returned for it


def form_search_query(question: str, patient: PatientContext) -> str:
    prompt = f"Patient context:\n{patient.as_query_text()}\n\nQuestion: {question}"
    result, _usage = get_client(Role.ANSWER_ENGINE).chat_json(
        SEARCH_QUERY_SYSTEM, prompt, SEARCH_QUERY_SCHEMA, max_tokens=300)
    return result["search_query"]


def seed(question: str, patient: PatientContext, min_grade: int,
        top_k: int | None = None, weights: dict[str, int] | None = None) -> SeedResult:
    """`weights` is a practitioner's own per-document grade override
    (vault.get_source_weights()) — applied here, in Python, rather than
    as a Cypher WHERE clause (store.seed_chunks_by_vector/_fulltext
    deliberately return unfiltered candidates) so a source the
    practitioner explicitly up-weighted above min_grade can still seed
    the traversal even if the shared admin grade alone would have
    excluded it, matching fetch_hop_neighbors' same weight-aware check
    at every later hop."""
    top_k = top_k or cfg.traversal_seed_top_k
    weights = weights or {}
    search_query = form_search_query(question, patient)

    embedding = get_client(Role.EMBEDDER).embed([search_query])[0]
    vector_hits = store.seed_chunks_by_vector(embedding, top_k)
    fulltext_hits = store.seed_chunks_by_fulltext(search_query, top_k)

    records: dict[str, dict] = {}
    for hit in (*vector_hits, *fulltext_hits):
        records.setdefault(hit["id"], hit)
    chunk_ids = [
        cid for cid, r in records.items()
        if weights.get(r.get("document_id"), r.get("grade", 0)) >= min_grade
    ]
    records = {cid: records[cid] for cid in chunk_ids}

    for entity in store.entities_mentioned_by_chunks(chunk_ids):
        records.setdefault(entity["id"], entity)

    entity_ids = [rid for rid, r in records.items() if not store.is_chunk(r)]
    return SeedResult(
        search_query=search_query,
        seed_chunk_ids=chunk_ids,
        seed_entity_ids=entity_ids,
        seed_records=records,
    )
