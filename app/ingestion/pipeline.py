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
from concurrent.futures import ThreadPoolExecutor

from ..clients.llm_client import NO_THINKING, Role, get_client
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


def _reader_sample(text: str, budget: int = 40_000) -> str:
    """Beginning + middle + end slices, not a plain head-truncate — Reader
    writes a title/summary/grade for the *whole* document, so a source
    whose substance is concentrated past the first `budget` characters
    (an abstract-then-appendices paper, a long transcript) would
    otherwise get graded/summarized on its intro alone. Still bounded,
    unlike full chunk-and-stitch (extract_article) — that exists because
    verbatim reproduction can't skip anything; Reader's job is already a
    lossy summary, so a representative sample is honest, not a shortcut.
    40_000 matches _SAFE_INPUT_CHARS below (same conservative chars/token
    math, verified safe there) — kept as a literal default here rather
    than importing that name forward, since it's defined later in this
    module and Reader's own max_tokens=2_000 leaves even more headroom
    than extract_article's 20_000 does anyway.

    Found live: a real ~39K-token document still exceeded the dedicated
    Reader deployment's 40_960 ceiling even after max_tokens was cut to
    2_000 (input alone left ~1 token of headroom) — the input itself has
    to be bounded, not just the requested output.
    """
    if len(text) <= budget:
        return text
    third = budget // 3
    start, mid_point = text[:third], len(text) // 2
    middle = text[mid_point - third // 2: mid_point + third // 2]
    end = text[-third:]
    return (
        f"{start}\n\n[... middle of document ...]\n\n{middle}"
        f"\n\n[... end of document ...]\n\n{end}"
    )


def read_source(text: str, filename: str, kind: str, origin: str,
                known_topics: list[str] | None = None) -> dict:
    shelves = known_topics or []
    prompt = (
        f"Topics already used in this library (reuse where one fits):\n"
        f"{', '.join(sorted(shelves)) or '(the library is empty)'}\n\n"
        f"Filename: {filename}\nKind: {kind}\nStated origin: {origin}\n\n"
        f"Source text:\n---\n{_reader_sample(text)}\n---"
    )
    # max_tokens=2_000, not chat_json()'s 20_000 default: READER_SCHEMA's
    # output (a title, 2-3 sentence summary, up to 4 topics, a grade) never
    # needs anywhere near that, and the default reserving 20_000 output
    # tokens on top of a large source's real input was enough on its own to
    # exceed the dedicated Reader deployment's 40_960 total-token ceiling —
    # a real BadRequestError hit live on a real staged document (~21K input
    # tokens), not a hypothetical.
    card, _usage = get_client(Role.READER).chat_json(
        READER_SYSTEM, prompt, READER_SCHEMA, max_tokens=2_000, extra_body=NO_THINKING)
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


# Ceiling math for one extract_article() call: the dedicated Qwen3-32B
# deployment Reader runs on caps max_model_len at 40_960 tokens, input +
# output combined, and hard-errors (openai.BadRequestError) above it —
# same trap chat_json() hit, see app/clients/llm_client.py. max_tokens is
# fixed at 20_000 (comfortably covers reproducing even a full chunk
# verbatim — this extraction never summarizes, so output is never larger
# than input), which leaves ~20_960 tokens of headroom for input + system
# prompt. Using a conservative 3 chars/token (worse than English prose's
# typical ~4, same spirit as checker.py's _MAX_EVIDENCE_CHARS headroom
# choice), 40_000 input chars is only ~13,334 tokens — plus the ~150-token
# system prompt and 20_000 max_tokens, that's ~33,500 of the 40_960
# ceiling, leaving real margin for tokenizer variance. 40_000 chars is
# also the exact size this function's single-call path already ran at
# safely in production before this fix (it used to hard-truncate to
# exactly this), so it's a doubly-verified safe chunk size, not just a
# fresh estimate.
_SAFE_INPUT_CHARS = 40_000


def _chunk_text(text: str, max_chars: int = _SAFE_INPUT_CHARS) -> list[str]:
    """Split text into pieces no larger than max_chars, for the chunk-
    and-stitch fallback below. Pure and network-free so the "should this
    input be chunked, and into how many pieces" decision is unit-testable
    without hitting the LLM.

    Prefers to break at a paragraph boundary, then a sentence boundary,
    only falling back to a hard character cut if neither exists near the
    target size — scraper.py's _strip_text() already joins block-level
    page content with '\\n', so a paragraph break is almost always a real
    content edge, not a mid-sentence cut. Deliberately no overlap between
    chunks: extract_article() reproduces kept content verbatim rather
    than summarizing across a boundary, so overlapping text would just
    get reproduced by both calls and show up twice in the stitched
    result — splitting cleanly at a real edge avoids the mid-sentence-cut
    problem overlap exists to solve, without that duplication risk.
    """
    if len(text) <= max_chars:
        return [text]
    chunks = []
    while len(text) > max_chars:
        window = text[:max_chars]
        split_at = window.rfind("\n\n")
        if split_at < max_chars // 2:
            split_at = window.rfind("\n")
        if split_at < max_chars // 2:
            split_at = window.rfind(". ")
            if split_at != -1:
                split_at += 1  # keep the period with the sentence it ends
        if split_at < max_chars // 2:
            split_at = max_chars  # nothing reasonable nearby — hard cut
        chunks.append(text[:split_at])
        text = text[split_at:]  # keep the boundary chars so chunks reconstruct exactly
    if text:
        chunks.append(text)
    return chunks


def _extract_chunk(chunk_text: str, url: str) -> str:
    """One extract_article() call over one chunk. Split out so both the
    single-call path and the multi-chunk fallback share identical prompt
    wiring — a chunked extraction must behave exactly like the unchunked
    one, just run more than once."""
    text, _usage = get_client(Role.READER).chat_text(
        EXTRACT_ARTICLE_SYSTEM,
        f"URL: {url}\n\nPage text:\n---\n{chunk_text}\n---",
        max_tokens=20_000,
        extra_body=NO_THINKING,
    )
    return text


def extract_article(stripped_text: str, url: str) -> str:
    """Plain-text output, not a JSON-schema call — the output *is* the
    document body. Role.READER — a bounded extraction task, not one that
    needs a stronger model.

    Single call for anything that fits in one (the common case, unchanged
    behavior/latency from before this fix). Only when stripped_text is
    long enough to blow the real token ceiling (see _SAFE_INPUT_CHARS
    above) does it split into sequential chunks and run one call per
    chunk in parallel — safe because this extraction is verbatim, not
    summarization: each chunk's kept content stands on its own, so there's
    no cross-chunk meaning to merge, just text to stitch back in order.
    Same ThreadPoolExecutor convention as ingest()'s extract_graph() fan-
    out below.
    """
    chunks = _chunk_text(stripped_text)
    if len(chunks) == 1:
        return _extract_chunk(chunks[0], url)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda c: _extract_chunk(c, url), chunks))
    return "".join(results)


def extract_graph(passage_text: str) -> dict:
    """One KG-builder call for one passage. Returns {entities, relationships}
    in the shape store.ingest_document() expects."""
    prompt = f"Passage:\n---\n{passage_text}\n---"
    result, _usage = get_client(Role.GRAPH_BUILDER).chat_json(
        KG_BUILDER_SYSTEM, prompt, KG_BUILDER_SCHEMA, extra_body=NO_THINKING)
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
        MERGE_SCHEMA, extra_body=NO_THINKING,
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
    #
    # Run concurrently — each passage's extract_graph() call is fully
    # independent (no shared state, no ordering dependency), and this
    # used to run one call, wait, next call: live-timed at ~26s for 10
    # passages, ~44% of a real ingest's total time (specs/v6.1/01).
    # max_workers=8 is a plain default, not tuned against a real Nebius
    # rate limit — lower it if a large document ever triggers 429s.
    entities_per_passage: list[list[dict] | None] = [None] * len(passages)
    all_relationships: list[dict] = []

    def _extract(i: int, text: str) -> tuple[int, list[dict], list[dict]]:
        try:
            graph = extract_graph(text)
            return i, graph["entities"], graph["relationships"]
        except Exception as exc:
            logging.warning("knowledge-graph extraction failed for a passage of %s: %s",
                            filename, exc)
            return i, [], []

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_extract, i, p["text"]) for i, p in enumerate(passages)]
        for future in futures:
            i, entities, rels = future.result()
            entities_per_passage[i] = entities
            all_relationships.extend(rels)

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
