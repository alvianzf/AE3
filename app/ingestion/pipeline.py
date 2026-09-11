"""Ingestion: new source in -> Document + Chunks + Entities + typed
relationships in the graph, idempotent on content_hash.

    Reader (Qwen3.6-27B)        -> source card (title/summary/topics/grade)
    chunk_pages()                -> passages (app/graph/store.py, unchanged
                                     chunking logic, schema-agnostic)
    Embedder (Qwen3-Embedding-8B) -> one embedding per chunk
    KG-builder (MedGemma-27B)    -> entities + relationships per chunk
    store.ingest_document()      -> one write, all of the above together
"""
from __future__ import annotations

import logging

from ..clients.llm_client import Role, get_client
from ..graph import store

READER_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Short descriptive title."},
        "summary": {"type": "string",
                    "description": "2-3 sentences on what this source covers."},
        "topics": {"type": "array", "items": {"type": "string"},
                   "description": "1-4 topics, taken from the library's topic "
                                  "list wherever one fits."},
        "suggested_grade": {"type": "integer",
                            "description": "Reliability 1-10. Peer-reviewed "
                                           "guidelines and clinical protocols score "
                                           "high; podcasts, blogs and anecdote score "
                                           "low."},
        "author": {"type": "string", "description": "Empty string if not stated."},
        "published": {"type": "string", "description": "Empty string if not stated."},
        "reference": {"type": "string", "description": "Empty string if none."},
    },
    "required": ["title", "summary", "topics", "suggested_grade", "author",
                 "published", "reference"],
    "additionalProperties": False,
}

READER_SYSTEM = (
    "You prepare sources for a clinical knowledge library. Read the source, "
    "title it, summarise it, tag its topics, record what it says about its own "
    "provenance, and propose a reliability grade from 1 to 10 based on the "
    "strength of its evidence and the authority of its origin. Be honest about "
    "weak sources — the grade decides what's allowed to reach a traversal. "
    "For author/published/reference: report only what the text itself states; "
    "an empty string beats a fabricated citation.\n\n"
    "Topics are the shelves a practitioner browses by — reuse an existing one "
    "whenever it genuinely fits (shown to you below); coin a new one only when "
    "nothing existing covers the source."
)

# Extensible on purpose — MedGemma's actual output decides what's real, this
# is guidance for the extraction prompt, not an enforced enum (see
# app/graph/store.py's sanitize_relationship_type for how a novel type gets
# made safe to write, not rejected).
SUGGESTED_ENTITY_TYPES = [
    "Condition", "Medication", "Symptom", "LabFinding", "Procedure",
    "AnatomicalSite",
]
SUGGESTED_RELATIONSHIP_TYPES = [
    "TREATS", "CAUSES", "CONTRAINDICATED_WITH", "INDICATES", "INTERACTS_WITH",
]

KG_BUILDER_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string",
                             "description": "A clinical category, e.g. " +
                                            ", ".join(SUGGESTED_ENTITY_TYPES) +
                                            " — use another if none fits."},
                },
                "required": ["name", "type"],
                "additionalProperties": False,
            },
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "head": {"type": "string", "description": "An entity name above."},
                    "rel_type": {"type": "string",
                                "description": "A relationship type, e.g. " +
                                               ", ".join(SUGGESTED_RELATIONSHIP_TYPES) +
                                               " — use another if none fits."},
                    "tail": {"type": "string", "description": "An entity name above."},
                },
                "required": ["head", "rel_type", "tail"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["entities", "relationships"],
    "additionalProperties": False,
}

KG_BUILDER_SYSTEM = (
    "You extract a clinical knowledge graph from one passage of a document.\n\n"
    "List the clinical entities this passage actually discusses — conditions, "
    "medications, symptoms, lab findings, procedures, anatomical sites, or "
    "another category if none of those fit. Use the passage's own terminology, "
    "not an abbreviation you'd have to expand from outside knowledge.\n\n"
    "Then list the relationships this passage explicitly states or clearly "
    "implies between those entities — what treats what, what causes what, what's "
    "contraindicated with what, what indicates what, what interacts with what, or "
    "another relationship type if none of those fit. Only relationships the "
    "passage actually supports — do not infer a relationship from general "
    "medical knowledge the passage itself doesn't state."
)


def read_source(text: str, filename: str, kind: str, origin: str,
                known_topics: list[str] | None = None) -> dict:
    shelves = known_topics or []
    prompt = (
        f"Topics already used in this library (reuse where one fits):\n"
        f"{', '.join(sorted(shelves)) or '(the library is empty)'}\n\n"
        f"Filename: {filename}\nKind: {kind}\nStated origin: {origin}\n\n"
        f"Source text:\n---\n{text}\n---"
    )
    card, _usage = get_client(Role.READER).chat_json(READER_SYSTEM, prompt, READER_SCHEMA)
    card["suggested_grade"] = max(1, min(10, int(card["suggested_grade"])))
    card["topics"] = [t.strip().lower() for t in card["topics"] if t.strip()][:4]
    for f in ("author", "published", "reference"):
        card[f] = card.get(f, "").strip()
    return card


EXTRACT_ARTICLE_SYSTEM = (
    "You are given the text content of a web page, already stripped of "
    "script/style tags. Extract only the main article/content text — the "
    "words a human reader came to this page to read. Discard navigation "
    "menus, headers, footers, cookie banners, ads, related-article lists, "
    "comment sections, and site chrome.\n\n"
    "Do not summarize, rephrase, shorten, or otherwise alter the content "
    "you keep. Reproduce it verbatim, word for word, exactly as it appears "
    "in the source. Your only job is deciding what is content and what is "
    "chrome — never editing the content itself."
)


def extract_article(stripped_text: str, url: str) -> str:
    """Plain-text output, not a JSON-schema call — the output *is* the
    document body. Role.READER — a bounded extraction task, not one that
    needs a stronger model."""
    text, _usage = get_client(Role.READER).chat_text(
        EXTRACT_ARTICLE_SYSTEM,
        f"URL: {url}\n\nPage text:\n---\n{stripped_text[:40000]}\n---",
        max_tokens=100_000,
    )
    return text


def extract_graph(passage_text: str) -> dict:
    """One KG-builder call for one passage. Returns {entities, relationships}
    in the shape store.ingest_document() expects."""
    prompt = f"Passage:\n---\n{passage_text}\n---"
    result, _usage = get_client(Role.GRAPH_BUILDER).chat_json(
        KG_BUILDER_SYSTEM, prompt, KG_BUILDER_SCHEMA, max_tokens=100_000)
    return result


MERGE_SCHEMA = {
    "type": "object",
    "properties": {
        "groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "canonical": {"type": "string", "description": "The label to keep."},
                    "aliases": {"type": "array", "items": {"type": "string"},
                                "description": "Labels to fold into it."},
                },
                "required": ["canonical", "aliases"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["groups"],
    "additionalProperties": False,
}

MERGE_SYSTEM = (
    "You tidy the entity index of a clinical knowledge graph. You are given the "
    "entity names currently in use. Some are the same idea written differently, "
    "and while they stay separate the graph cannot connect the material that "
    "uses them.\n\n"
    "Group only labels that mean the SAME thing — an abbreviation and its "
    "expansion, a synonym, a spelling or plural variant, a possessive. Choose the "
    "clearest full clinical name as the canonical form.\n\n"
    "Do NOT group things that are merely related, or a specific case under a "
    "general one — merging those would make the graph claim two different "
    "clinical entities are the same thing.\n\n"
    "Return only the groups that need merging. An empty list is the right "
    "answer when nothing does."
)


def suggest_entity_merges(names: list[str]) -> list[dict]:
    """Ask which existing Entity names are the same idea. Returns merge
    groups for store.merge_entities()."""
    if len(names) < 2:
        return []
    result, _usage = get_client(Role.GRAPH_BUILDER).chat_json(
        MERGE_SYSTEM, "Entity names in use:\n" + "\n".join(f"- {n}" for n in sorted(names)),
        MERGE_SCHEMA, max_tokens=100_000,
    )
    groups = []
    for g in result["groups"]:
        canonical = " ".join(g["canonical"].lower().split())
        aliases = [" ".join(a.lower().split()) for a in g["aliases"]]
        aliases = [a for a in aliases if a and a != canonical and a in names]
        if canonical and aliases:
            groups.append({"canonical": canonical, "aliases": aliases})
    return groups


def ingest(*, text: str, filename: str, kind: str, origin: str,
          pages: list[tuple[int | None, str]] | None = None,
          original: tuple | None = None) -> dict:
    """Full pipeline: read -> chunk -> embed -> extract graph -> write.

    `pages` is [(page_number, text), ...] (None for unpaginated text) —
    same shape store.chunk_pages() already expects. Raises ValueError if
    this exact content has already been ingested (idempotency check,
    before any LLM calls run — no point paying for re-reading a duplicate).
    """
    digest = store.content_hash(text)
    existing = store.find_by_hash(digest)
    if existing is not None:
        raise ValueError(f"Already ingested as '{existing['title']}' ({existing['id']})")

    card = read_source(text, filename, kind, origin, store.facets()["topics"])
    passages = store.chunk_pages(pages or [(None, text)])
    if not passages:
        raise ValueError("Source produced no passages after chunking.")

    embeddings = get_client(Role.EMBEDDER).embed([p["text"] for p in passages])
    for i, p in enumerate(passages):
        p["embedding"] = embeddings[i] if i < len(embeddings) else None

    # Graph-building is additive — never lose the document, or another
    # passage's already-extracted entities, over one passage's failure.
    # Caught per-passage, not around the whole loop, matching
    # app/main.py's inline copy of this same flow (_ingest_pages) — a
    # transient extraction error here used to abort the whole ingest.
    entities_per_passage: list[list[dict]] = []
    all_relationships: list[dict] = []
    for p in passages:
        try:
            graph = extract_graph(p["text"])
            entities_per_passage.append(graph["entities"])
            all_relationships.extend(graph["relationships"])
        except Exception as exc:
            logging.warning("knowledge-graph extraction failed for a passage of %s: %s",
                            filename, exc)
            entities_per_passage.append([])

    return store.ingest_document(
        title=card["title"], filename=filename, kind=kind, origin=origin,
        grade=card["suggested_grade"], source_card_summary=card["summary"],
        topics=card["topics"], passages=passages, digest=digest, body=text,
        author=card["author"], published=card["published"],
        reference=card["reference"],
        page_count=max((pn or 0 for pn, _ in (pages or [])), default=0),
        entities_per_passage=entities_per_passage, relationships=all_relationships,
        original=original,
    )
