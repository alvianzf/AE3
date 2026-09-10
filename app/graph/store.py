"""The knowledge graph: Document/Chunk/Entity, replacing the old
Source/Chunk/Topic/Concept schema (app/knowledge.py, retired).

    (:Document {id, title, source_card_summary, topics: [...], grade,
                ingested_at, content_hash, body, ...})
      -[:HAS_CHUNK]->(:Chunk {id, text, embedding, chunk_index})
    (:Chunk)-[:NEXT_CHUNK]->(:Chunk)          reading-order, within a doc
    (:Chunk)-[:MENTIONS]->(:Entity {id, name, type})
    (:Entity)-[:TREATS|CAUSES|...]->(:Entity)  typed clinical relationships,
                                                 extracted by the KG-builder
                                                 role — see upsert_relationship

`grade` (the reliability threshold) is carried forward from the old Source
schema onto Document — the product's existing trust mechanic (MIN_GRADE,
the grade slider) is a stated safety requirement, not something this
rewrite drops.

Topics are a Document property array, not separate :Topic nodes (per the
schema this module implements) — facets()/coverage() below aggregate over
that array with UNWIND instead of traversing a TAGGED edge.

Entity resolution is basic, on purpose (see upsert_entity's docstring) —
flagged as a real TODO, not silently over-engineered on this first pass.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .. import originals
from ..config import get_config
from .driver import session

cfg = get_config()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Name canonicalisation ------------------------------------------------
# Ported unchanged from the old knowledge.py's canon()/canon_all() — the
# alias table already covers common clinical abbreviations, and this is
# also the entity-resolution key (see upsert_entity below): two mentions
# that canonicalise to the same string become one Entity node via MERGE.

ALIASES = {
    "vit d": "vitamin d", "vitd": "vitamin d", "25(oh)d": "vitamin d",
    "hashimoto's": "hashimoto thyroiditis", "hashimotos": "hashimoto thyroiditis",
    "autoimmune thyroid disease": "hashimoto thyroiditis", "ht": "hashimoto thyroiditis",
    "tsh": "thyroid stimulating hormone", "t4": "thyroxine", "t3": "triiodothyronine",
    "pcos": "polycystic ovary syndrome",
    "ir": "insulin resistance", "t2dm": "type 2 diabetes",
    "amh": "anti-mullerian hormone", "fsh": "follicle stimulating hormone",
    "bmi": "body mass index", "vte": "venous thromboembolism",
    "dvt": "venous thromboembolism",
    "gi": "gastrointestinal", "coeliac": "coeliac disease", "celiac": "coeliac disease",
    "celiac disease": "coeliac disease",
    "tiredness": "fatigue", "exhaustion": "fatigue",
    "hair loss": "hair thinning", "hair shedding": "hair thinning",
    "malabsorption syndrome": "malabsorption",
}
_TARGETS = frozenset(ALIASES.values())
_KEEP_S = ("is", "ss", "us", "es", "sis", "itis", "osis", "asis")


def canon(name: str) -> str:
    n = " ".join(str(name).lower().split()).strip(" .,:;()[]").replace("’", "'")
    if n in _TARGETS:
        return n
    if n in ALIASES:
        return ALIASES[n]
    for variant in (n.replace("'s", ""), n[:-1] if n.endswith("s") else n):
        variant = variant.strip()
        if variant in ALIASES:
            return ALIASES[variant]
        if variant in _TARGETS:
            return variant
    if len(n) > 4 and n.endswith("s") and not n.endswith(_KEEP_S):
        n = n[:-1]
    return n


def canon_all(names) -> list[str]:
    seen, out = set(), []
    for raw in names or []:
        c = canon(raw)
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


# --- Duplicate detection ---------------------------------------------------

def content_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


def find_by_hash(digest: str) -> dict | None:
    with session() as s:
        rec = s.run(
            "MATCH (doc:Document {content_hash: $h}) RETURN doc.id AS id", h=digest,
        ).single()
    return get_document(rec["id"]) if rec else None


# --- Chunking ---------------------------------------------------------------

def chunk_pages(pages: list[tuple[int | None, str]]) -> list[dict]:
    """Split into passages, carrying the page each one came from.

    Unchanged from the old knowledge.py — chunk_size/chunk_overlap are
    configurable (config.py), the algorithm isn't schema-specific.
    """
    paras: list[tuple[int | None, str]] = []
    for page_no, text in pages:
        for para in text.split("\n\n"):
            para = para.strip()
            if para:
                paras.append((page_no, para))

    passages: list[dict] = []
    buf, buf_pages = "", []

    def flush():
        if buf:
            seen = [p for p in buf_pages if p is not None]
            passages.append({
                "text": buf,
                "page_start": min(seen) if seen else None,
                "page_end": max(seen) if seen else None,
            })

    for page_no, para in paras:
        while len(para) > cfg.chunk_size * 2:
            flush()
            buf, buf_pages = para[: cfg.chunk_size], [page_no]
            flush()
            buf, buf_pages = "", []
            para = para[cfg.chunk_size - cfg.chunk_overlap:]
        if buf and len(buf) + len(para) + 2 > cfg.chunk_size:
            flush()
            tail = buf[-cfg.chunk_overlap:] if cfg.chunk_overlap else ""
            buf = f"{tail}\n\n{para}" if tail else para
            buf_pages = ([buf_pages[-1]] if tail and buf_pages else []) + [page_no]
        else:
            buf = f"{buf}\n\n{para}" if buf else para
            buf_pages.append(page_no)
    flush()
    return passages


# --- Ingestion --------------------------------------------------------------

def ingest_document(
    *, title: str, filename: str, kind: str, origin: str, grade: int,
    source_card_summary: str, topics: list[str], passages: list[dict],
    digest: str, body: str, author: str = "", published: str = "",
    reference: str = "", page_count: int = 0,
    entities_per_passage: list[list[dict]] | None = None,
    relationships: list[dict] | None = None,
    original: tuple[bytes | Path, str, str] | None = None,
) -> dict:
    """Write a read-and-graded document plus its chunks, entities, and
    typed relationships. Idempotent: content_hash is a uniqueness
    constraint, so re-ingesting the same body raises
    neo4j.exceptions.ConstraintError (caller — ingestion/pipeline.py —
    checks find_by_hash() first for a clean error instead of relying on
    the constraint alone).

    `entities_per_passage[i]` is the list of {name, type} dicts the
    KG-builder role extracted for passages[i]; `relationships` is
    [{head, rel_type, tail}, ...] across the whole document (entities can
    relate across passage boundaries, e.g. a drug mentioned in one
    passage and a condition it treats mentioned in another).
    """
    document_id = str(uuid.uuid4())
    total = len(passages)
    entities_per_passage = entities_per_passage or [[] for _ in passages]
    rows = [
        {"id": f"{document_id}:{i}", "text": p["text"], "chunk_index": i,
         "page_start": p["page_start"], "page_end": p["page_end"],
         "embedding": p.get("embedding")}
        for i, p in enumerate(passages)
    ]
    entity_rows = [
        {"chunk_index": i, "name": canon(e["name"]), "type": e.get("type") or "Unknown"}
        for i, ents in enumerate(entities_per_passage) for e in ents if e.get("name")
    ]

    with session() as s:
        s.run(
            """
            CREATE (doc:Document {id: $id, title: $title, filename: $filename,
                                  kind: $kind, origin: $origin, grade: $grade,
                                  source_card_summary: $summary, ingested_at: $now,
                                  content_hash: $digest, body: $body, topics: $topics,
                                  author: $author, published: $published,
                                  reference: $reference, page_count: $page_count,
                                  char_count: $char_count, passage_count: $total})
            FOREACH (row IN $rows |
              CREATE (c:Chunk {id: row.id, text: row.text, chunk_index: row.chunk_index,
                               page_start: row.page_start, page_end: row.page_end,
                               embedding: row.embedding})
              CREATE (doc)-[:HAS_CHUNK]->(c))
            """,
            id=document_id, title=title, filename=filename, kind=kind, origin=origin,
            grade=grade, summary=source_card_summary, now=_now(), digest=digest,
            body=body, topics=topics, author=author, published=published,
            reference=reference, page_count=page_count, char_count=len(body),
            total=total, rows=rows,
        )
        _link_chunks_in_order(s, document_id)
        if entity_rows:
            s.run(
                """
                UNWIND $rows AS row
                MATCH (doc:Document {id: $id})-[:HAS_CHUNK]->(c:Chunk {chunk_index: row.chunk_index})
                MERGE (e:Entity {name: row.name})
                  ON CREATE SET e.id = randomUUID(), e.type = row.type
                MERGE (c)-[:MENTIONS]->(e)
                """,
                id=document_id, rows=entity_rows,
            )
        for rel in (relationships or []):
            upsert_relationship(rel["head"], rel["rel_type"], rel["tail"], s)

        if original:
            content, name, media_type = original
            if isinstance(content, Path):
                size = content.stat().st_size
                saved = originals.save_from_path(document_id, content, name)
            else:
                size = len(content)
                saved = originals.save(document_id, content, name)
            if saved:
                s.run(
                    "MATCH (doc:Document {id: $id}) SET doc.original_name = $name, "
                    "doc.original_media_type = $media_type, doc.original_bytes = $size",
                    id=document_id, name=name, media_type=media_type, size=size,
                )
    log("admin", "ingest",
        f"{title} — {total} passages, {page_count or 0} pages, grade {grade}")
    return get_document(document_id)


def link_document(document_id: str, entities_per_passage: list[list[dict]],
                  relationships: list[dict] | None = None) -> int:
    """Attach entities/relationships to an already-ingested document —
    for documents ingested before graph-building ran, or where it failed
    (see unlinked_documents() above and app/main.py's /api/relink).
    Returns edges written."""
    entity_rows = [
        {"chunk_index": i, "name": canon(e["name"]), "type": e.get("type") or "Unknown"}
        for i, ents in enumerate(entities_per_passage) for e in ents if e.get("name")
    ]
    relationships = relationships or []
    if not entity_rows and not relationships:
        return 0
    with session() as s:
        if entity_rows:
            s.run(
                """
                UNWIND $rows AS row
                MATCH (doc:Document {id: $id})-[:HAS_CHUNK]->(c:Chunk {chunk_index: row.chunk_index})
                MERGE (e:Entity {name: row.name})
                  ON CREATE SET e.id = randomUUID(), e.type = row.type
                MERGE (c)-[:MENTIONS]->(e)
                """,
                id=document_id, rows=entity_rows,
            )
        for rel in relationships:
            upsert_relationship(rel["head"], rel["rel_type"], rel["tail"], s)
    return len(entity_rows) + len(relationships)


def _link_chunks_in_order(s, document_id: str) -> None:
    s.run(
        """
        MATCH (doc:Document {id: $id})-[:HAS_CHUNK]->(c:Chunk)
        WITH c ORDER BY c.chunk_index
        WITH collect(c) AS cs
        UNWIND range(0, size(cs) - 2) AS i
          WITH cs[i] AS a, cs[i + 1] AS b
          MERGE (a)-[:NEXT_CHUNK]->(b)
        """,
        id=document_id,
    )


# --- Entity/relationship upsert (also used by ingestion/pipeline.py directly) -

_REL_TYPE_RE = re.compile(r"[^A-Z0-9_]")


def sanitize_relationship_type(raw: str) -> str:
    """Cypher relationship types can't be query-parameterized, so a
    KG-builder-extracted type string is sanitized to a safe identifier
    (uppercase, [A-Z0-9_] only) before being interpolated into a query —
    not restricted to a fixed taxonomy (the spec explicitly says not to
    force one), just made safe to use as an identifier. Falls back to
    RELATED_TO if sanitization leaves nothing usable."""
    cleaned = _REL_TYPE_RE.sub("_", raw.strip().upper().replace(" ", "_")).strip("_")
    return cleaned or "RELATED_TO"


def upsert_entity(name: str, entity_type: str, s=None) -> str:
    """Resolve-or-create an Entity by normalized name.

    Basic resolution only, as specced: same normalized name = same node,
    regardless of context. TODO (flagged, not silently ignored): this
    will incorrectly merge genuinely distinct entities that happen to
    normalize identically in different contexts (e.g. an abbreviation
    that means different things in different specialties), and won't
    catch two real synonyms that don't share a normalized string and
    aren't in the ALIASES table above. A smarter pass — embedding-based
    entity linking, or a human review queue for low-confidence merges —
    is real follow-up work, not done here.
    """
    key = canon(name)
    close = s is None
    s = s or session()
    try:
        rec = s.run(
            "MERGE (e:Entity {name: $name}) "
            "ON CREATE SET e.id = randomUUID(), e.type = $type "
            "RETURN e.id AS id",
            name=key, type=entity_type or "Unknown",
        ).single()
        return rec["id"]
    finally:
        if close:
            s.close()


def upsert_relationship(head_name: str, rel_type: str, tail_name: str, s=None) -> None:
    rel = sanitize_relationship_type(rel_type)
    close = s is None
    s = s or session()
    try:
        s.run(
            f"""
            MERGE (h:Entity {{name: $head}})
              ON CREATE SET h.id = randomUUID(), h.type = 'Unknown'
            MERGE (t:Entity {{name: $tail}})
              ON CREATE SET t.id = randomUUID(), t.type = 'Unknown'
            MERGE (h)-[:{rel}]->(t)
            """,
            head=canon(head_name), tail=canon(tail_name),
        )
    finally:
        if close:
            s.close()


# --- Admin surface: read/manage documents -----------------------------------

# specs/v4.1's admin Library page (its layout explicitly frozen) reads
# `summary`/`created_at` straight off the API response — this schema's
# real property names are source_card_summary/ingested_at (per the graph
# schema spec), so both are aliased back to the old names here at the API
# boundary rather than touching the frontend. Both names are returned
# (the real one and the alias) so any other caller can use either.
_CARD = """
    doc.id AS id, doc.title AS title, doc.filename AS filename,
    doc.kind AS kind, doc.origin AS origin, doc.grade AS grade,
    doc.source_card_summary AS source_card_summary,
    doc.source_card_summary AS summary,
    doc.ingested_at AS ingested_at, doc.ingested_at AS created_at,
    doc.author AS author, doc.published AS published,
    doc.reference AS reference, doc.page_count AS page_count,
    doc.char_count AS char_count, doc.content_hash AS content_hash,
    doc.topics AS topics, doc.original_name AS original_name,
    doc.original_media_type AS original_media_type,
    doc.original_bytes AS original_bytes
"""


def get_document(document_id: str) -> dict | None:
    with session() as s:
        rec = s.run(
            f"""
            MATCH (doc:Document {{id: $id}})
            OPTIONAL MATCH (doc)-[:HAS_CHUNK]->(c:Chunk)
            RETURN {_CARD}, count(DISTINCT c) AS chunks
            """,
            id=document_id,
        ).single()
        return dict(rec) if rec else None


SORTS = {
    "newest": "doc.ingested_at DESC",
    "oldest": "doc.ingested_at ASC",
    "grade_desc": "doc.grade DESC, doc.title",
    "grade_asc": "doc.grade ASC, doc.title",
    "title": "toLower(doc.title)",
}


def list_documents(search: str = "", topic: str = "", kind: str = "",
                   min_grade: int = 1, max_grade: int = 10,
                   sort: str = "newest", page: int = 1,
                   per_page: int = 10) -> dict:
    filters = ["doc.grade >= $min_grade", "doc.grade <= $max_grade"]
    params: dict = {"min_grade": min_grade, "max_grade": max_grade}
    if search.strip():
        filters.append(
            "(toLower(doc.title) CONTAINS $q OR toLower(doc.source_card_summary) CONTAINS $q "
            "OR toLower(doc.origin) CONTAINS $q OR toLower(doc.author) CONTAINS $q "
            "OR toLower(doc.filename) CONTAINS $q "
            "OR toLower(coalesce(doc.body, '')) CONTAINS $q)")
        params["q"] = search.strip().lower()
    if kind.strip():
        filters.append("doc.kind = $kind")
        params["kind"] = kind.strip()
    if topic.strip():
        filters.append("$topic IN doc.topics")
        params["topic"] = topic.strip()

    where = " AND ".join(filters)
    order = SORTS.get(sort, SORTS["newest"])
    page = max(1, page)
    per_page = max(1, min(500, per_page))
    params |= {"skip": (page - 1) * per_page, "limit": per_page}

    with session() as s:
        total = s.run(
            f"MATCH (doc:Document) WHERE {where} RETURN count(doc) AS n", **params
        ).single()["n"]
        recs = s.run(
            f"""
            MATCH (doc:Document) WHERE {where}
            WITH doc ORDER BY {order} SKIP $skip LIMIT $limit
            OPTIONAL MATCH (doc)-[:HAS_CHUNK]->(c:Chunk)
            RETURN {_CARD}, count(DISTINCT c) AS chunks
            ORDER BY {order}
            """,
            **params,
        )
        documents = [dict(r) for r in recs]

    pages = max(1, (total + per_page - 1) // per_page)
    # "sources", not "documents" — specs/v4.1's admin Library page (layout
    # frozen) reads response.sources directly; same API-boundary-alias
    # treatment as _CARD's summary/created_at above.
    return {"sources": documents, "total": total, "page": min(page, pages),
            "pages": pages, "per_page": per_page}


def facets() -> dict:
    with session() as s:
        topics = [r["t"] for r in s.run(
            "MATCH (doc:Document) UNWIND doc.topics AS t "
            "RETURN DISTINCT t ORDER BY t")]
        kinds = [r["k"] for r in s.run(
            "MATCH (doc:Document) RETURN DISTINCT doc.kind AS k ORDER BY k")]
    return {"topics": topics, "kinds": kinds}


def document_text(document_id: str) -> dict | None:
    with session() as s:
        rec = s.run(
            f"MATCH (doc:Document {{id: $id}}) RETURN {_CARD}, doc.body AS body",
            id=document_id,
        ).single()
        if not rec:
            return None
        passages = s.run(
            """
            MATCH (doc:Document {id: $id})-[:HAS_CHUNK]->(c:Chunk)
            RETURN c.chunk_index AS chunk_index, c.text AS text,
                   c.page_start AS page_start, c.page_end AS page_end
            ORDER BY c.chunk_index
            """,
            id=document_id,
        )
        rows = [dict(p) for p in passages]

    card = dict(rec)
    if not card.get("body"):
        card["body"] = "\n\n".join(p["text"] for p in rows)
        card["body_reconstructed"] = True
    return {**card, "passages": rows}


def set_grade(document_id: str, grade: int) -> dict | None:
    with session() as s:
        s.run("MATCH (doc:Document {id: $id}) SET doc.grade = $grade",
              id=document_id, grade=grade)
    log("admin", "regrade", f"{document_id} → grade {grade}")
    return get_document(document_id)


def delete_document(document_id: str) -> None:
    with session() as s:
        s.run(
            """
            MATCH (doc:Document {id: $id})
            OPTIONAL MATCH (doc)-[:HAS_CHUNK]->(c:Chunk)
            DETACH DELETE c, doc
            """,
            id=document_id,
        )
    originals.delete(document_id)
    log("admin", "delete", document_id)


def catalogue(min_grade: int) -> list[dict]:
    """Every document at or above a grade threshold — used by the
    practitioner's per-source weighting page (app/main.py's
    GET /api/me/knowledge), not by retrieval (which is grade-filtered at
    the seed/hop level directly, see fetch_hop_neighbors above)."""
    with session() as s:
        recs = s.run(
            """
            MATCH (doc:Document) WHERE doc.grade >= $min_grade
            OPTIONAL MATCH (doc)-[:HAS_CHUNK]->(c:Chunk)
            RETURN doc.id AS id, doc.title AS title, doc.source_card_summary AS summary,
                   doc.grade AS grade, doc.origin AS origin, doc.kind AS kind,
                   doc.author AS author, doc.published AS published,
                   doc.topics AS topics, count(DISTINCT c) AS passages
            ORDER BY doc.grade DESC, doc.title
            """,
            min_grade=min_grade,
        )
        return [dict(r) for r in recs]


def entities_for(document_id: str, limit: int = 40) -> list[dict]:
    with session() as s:
        return [dict(r) for r in s.run(
            """
            MATCH (:Document {id: $id})-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(e:Entity)
            RETURN e.name AS name, e.type AS type, count(*) AS uses
            ORDER BY uses DESC, name LIMIT $limit
            """, id=document_id, limit=limit)]


def neighbours_of(document_id: str, limit: int = 6) -> list[dict]:
    """Other documents connected to this one, and the entities they share."""
    with session() as s:
        recs = s.run(
            """
            MATCH (:Document {id: $id})-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(e:Entity)
                  <-[:MENTIONS]-(:Chunk)<-[:HAS_CHUNK]-(other:Document)
            WHERE other.id <> $id
            WITH other, collect(DISTINCT e.name) AS shared
            RETURN other.id AS id, other.title AS title, other.grade AS grade,
                   shared, size(shared) AS n
            ORDER BY n DESC, other.grade DESC LIMIT $limit
            """, id=document_id, limit=limit)
        return [dict(r) for r in recs]


def unlinked_documents() -> list[dict]:
    """Documents with no entity mentions — ingested before KG-building ran,
    or extraction failed. Mirrors the old unlinked_sources()."""
    with session() as s:
        recs = s.run(
            """
            MATCH (doc:Document)
            WHERE NOT EXISTS { (doc)-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(:Entity) }
            RETURN doc.id AS id, doc.title AS title
            ORDER BY doc.ingested_at
            """
        )
        return [dict(r) for r in recs]


def all_entities() -> list[dict]:
    with session() as s:
        return [dict(r) for r in s.run(
            "MATCH (e:Entity) RETURN e.name AS name, e.type AS type ORDER BY e.name")]


def merge_entities(groups: list[dict]) -> int:
    """Fold alias Entity nodes into their canonical node, moving MENTIONS
    and every typed relationship with them. `groups` is
    [{canonical, aliases: [...]}, ...]. Returns nodes absorbed.

    **Requires the APOC plugin** (apoc.merge.relationship) — unlike the
    rest of this module, arbitrary-typed relationship redirection can't
    be expressed in plain Cypher (a relationship type isn't a runtime
    value). Confirm APOC is installed on the target Neo4j instance before
    relying on this; it's an admin-only dedup tool, not on the ingestion
    or retrieval hot path, so a missing-APOC failure here is loud and
    low-stakes, not a silent data-quality issue.
    """
    merged = 0
    with session() as s:
        for g in groups:
            res = s.run(
                """
                MERGE (keep:Entity {name: $canonical})
                  ON CREATE SET keep.id = randomUUID(), keep.type = 'Unknown'
                WITH keep
                UNWIND $aliases AS alias
                MATCH (drop:Entity {name: alias})
                WHERE drop <> keep
                CALL (drop, keep) {
                  MATCH (drop)-[r]->(other) WHERE type(r) <> 'MENTIONS'
                  CALL apoc.merge.relationship(keep, type(r), {}, {}, other) YIELD rel
                  RETURN count(*) AS _out
                }
                CALL (drop, keep) {
                  MATCH (other)-[r]->(drop)
                  CALL apoc.merge.relationship(other, type(r), {}, {}, keep) YIELD rel
                  RETURN count(*) AS _in
                }
                DETACH DELETE drop
                RETURN count(*) AS n
                """,
                canonical=g["canonical"], aliases=g["aliases"],
            ).single()
            merged += res["n"] if res else 0
    return merged


def graph_stats() -> dict:
    with session() as s:
        rec = s.run(
            """
            CALL () { MATCH (e:Entity) RETURN count(e) AS entities }
            CALL () { MATCH (:Chunk)-[m:MENTIONS]->(:Entity) RETURN count(m) AS mentions }
            CALL () { MATCH (:Chunk)-[n:NEXT_CHUNK]->(:Chunk) RETURN count(n) AS order_edges }
            CALL () {
              MATCH (h:Entity)-[r]->(t:Entity) WHERE type(r) <> 'MENTIONS'
              RETURN count(r) AS typed_relationships
            }
            RETURN entities, mentions, order_edges, typed_relationships
            """
        ).single()
        return dict(rec)


def coverage() -> list[dict]:
    # "sources", not "documents" — same API-boundary-alias reasoning as
    # list_documents()/_CARD above (admin Library page's frozen layout).
    with session() as s:
        recs = s.run(
            """
            MATCH (doc:Document) UNWIND doc.topics AS topic
            OPTIONAL MATCH (doc)-[:HAS_CHUNK]->(c:Chunk)
            RETURN topic, count(DISTINCT doc) AS sources, count(DISTINCT c) AS chunks
            ORDER BY chunks DESC, topic
            """
        )
        return [dict(r) for r in recs]


def log(actor: str, action: str, detail: str) -> None:
    with session() as s:
        s.run(
            "CREATE (:AuditEvent {id: $id, ts: $ts, actor: $actor, "
            "action: $action, detail: $detail})",
            id=str(uuid.uuid4()), ts=_now(), actor=actor, action=action, detail=detail,
        )


def audit(limit: int = 100) -> list[dict]:
    with session() as s:
        recs = s.run(
            "MATCH (a:AuditEvent) RETURN a.id AS id, a.ts AS ts, a.actor AS actor, "
            "a.action AS action, a.detail AS detail ORDER BY a.ts DESC LIMIT $limit",
            limit=limit,
        )
        return [dict(r) for r in recs]


def stats() -> dict:
    with session() as s:
        rec = s.run(
            """
            CALL () { MATCH (doc:Document) RETURN count(doc) AS documents }
            CALL () { MATCH (c:Chunk) RETURN count(c) AS chunks }
            CALL () { MATCH (e:Entity) RETURN count(e) AS entities }
            RETURN documents, chunks, entities
            """
        ).single()
        return dict(rec)


# --- Retrieval support: seed search + per-hop traversal ---------------------
# Used by retrieval/seed_search.py and retrieval/traversal.py — kept here
# rather than in retrieval/ because these are still just Cypher against
# this module's schema, same reasoning as every other function above.

def seed_chunks_by_vector(embedding: list[float], top_k: int, min_grade: int) -> list[dict]:
    """Nearest chunks by cosine similarity, grade-filtered at the source."""
    with session() as s:
        recs = s.run(
            """
            CALL db.index.vector.queryNodes('chunk_embedding', $top_k, $embedding)
            YIELD node AS c, score
            MATCH (doc:Document)-[:HAS_CHUNK]->(c)
            WHERE doc.grade >= $min_grade
            RETURN c.id AS id, c.text AS text, c.chunk_index AS chunk_index,
                   doc.id AS document_id, doc.title AS document_title,
                   doc.grade AS grade, score
            ORDER BY score DESC
            """,
            embedding=embedding, top_k=top_k, min_grade=min_grade,
        )
        return [dict(r) for r in recs]


def seed_chunks_by_fulltext(query: str, top_k: int, min_grade: int) -> list[dict]:
    with session() as s:
        recs = s.run(
            """
            CALL db.index.fulltext.queryNodes('chunk_text_fulltext', $query)
            YIELD node AS c, score
            MATCH (doc:Document)-[:HAS_CHUNK]->(c)
            WHERE doc.grade >= $min_grade
            RETURN c.id AS id, c.text AS text, c.chunk_index AS chunk_index,
                   doc.id AS document_id, doc.title AS document_title,
                   doc.grade AS grade, score
            ORDER BY score DESC LIMIT $top_k
            """,
            query=query, top_k=top_k, min_grade=min_grade,
        )
        return [dict(r) for r in recs]


def seed_entities_by_fulltext(query: str, top_k: int) -> list[dict]:
    with session() as s:
        recs = s.run(
            """
            CALL db.index.fulltext.queryNodes('entity_name_fulltext', $query)
            YIELD node AS e, score
            RETURN e.id AS id, e.name AS name, e.type AS type, score
            ORDER BY score DESC LIMIT $top_k
            """,
            query=query, top_k=top_k,
        )
        return [dict(r) for r in recs]


def entities_mentioned_by_chunks(chunk_ids: list[str]) -> list[dict]:
    """The Entity nodes a set of chunks mentions — used to seed the
    traversal frontier with entity points alongside the seed chunks
    themselves (retrieval/seed_search.py)."""
    if not chunk_ids:
        return []
    with session() as s:
        recs = s.run(
            """
            MATCH (c:Chunk)-[:MENTIONS]->(e:Entity)
            WHERE c.id IN $ids
            RETURN DISTINCT e.id AS id, e.name AS name, e.type AS type
            """,
            ids=chunk_ids,
        )
        return [dict(r) for r in recs]


def fetch_hop_neighbors(frontier_ids: list[str], visited_ids: set[str],
                        min_grade: int, limit: int) -> list[dict]:
    """Unvisited neighbors of the current frontier, one hop out, in any
    direction and via any relationship type (MENTIONS, NEXT_CHUNK,
    HAS_CHUNK's reverse, or any typed entity-entity relationship the
    KG-builder produced) — deliberately not enumerating relationship
    types so a new type MedGemma introduces is traversable without a
    code change.

    Grade is only enforced on Chunk-type candidates (a Chunk's trust
    boundary is its parent Document's grade); Entity candidates pass
    through un-filtered here — an Entity by itself carries no clinical
    claim on its own, only the Chunks that mention it do, and those get
    filtered when *they're* reached. Capped at `limit` candidates,
    matching the hop's config.traversal_max_candidates_per_hop budget.
    """
    if not frontier_ids:
        return []
    with session() as s:
        recs = s.run(
            """
            UNWIND $frontier_ids AS fid
            MATCH (n {id: fid})-[r]-(neighbor)
            WHERE NOT neighbor.id IN $visited_ids AND neighbor.id IS NOT NULL
            WITH DISTINCT neighbor, type(r) AS via, labels(neighbor) AS labs
            OPTIONAL MATCH (doc:Document)-[:HAS_CHUNK]->(neighbor)
            RETURN neighbor.id AS id, labs AS labels, via,
                   neighbor.name AS name, neighbor.type AS entity_type,
                   neighbor.text AS text, neighbor.chunk_index AS chunk_index,
                   doc.id AS document_id, doc.title AS document_title, doc.grade AS grade
            LIMIT $limit
            """,
            frontier_ids=frontier_ids, visited_ids=list(visited_ids), limit=limit,
        )
        candidates = [dict(r) for r in recs]
    return [
        c for c in candidates
        if "Entity" in c["labels"] or (c.get("grade") is not None and c["grade"] >= min_grade)
    ]
