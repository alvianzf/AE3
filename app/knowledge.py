"""The clinic's knowledge library: a Neo4j source/passage/topic store.

Sources are ingested once (read, tagged, graded, split into passages). Retrieval
is card-based: the Librarian is shown the catalogue of source cards at or above
the requested grade and picks which sources to open, then those sources'
passages go to the Specialist. No embeddings are involved.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

import neo4j

from . import originals
from .config import get_config

cfg = get_config()

_driver: neo4j.Driver | None = None


def get_driver() -> neo4j.Driver:
    global _driver
    if _driver is None:
        _driver = neo4j.GraphDatabase.driver(
            cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password)
        )
    return _driver


def _session():
    return get_driver().session(database=cfg.neo4j_database)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Schema -------------------------------------------------------------------

def ensure_schema() -> None:
    """Create uniqueness constraints. Idempotent."""
    with _session() as s:
        s.run("CREATE CONSTRAINT source_id IF NOT EXISTS "
              "FOR (n:Source) REQUIRE n.id IS UNIQUE")
        s.run("CREATE CONSTRAINT chunk_id IF NOT EXISTS "
              "FOR (n:Chunk) REQUIRE n.id IS UNIQUE")
        s.run("CREATE CONSTRAINT topic_name IF NOT EXISTS "
              "FOR (n:Topic) REQUIRE n.name IS UNIQUE")
        s.run("CREATE CONSTRAINT concept_name IF NOT EXISTS "
              "FOR (n:Concept) REQUIRE n.name IS UNIQUE")
        # Makes a duplicate ingest fail at the database rather than relying on
        # the read-then-write check alone, which two concurrent uploads could
        # both pass.
        s.run("CREATE CONSTRAINT source_hash IF NOT EXISTS "
              "FOR (n:Source) REQUIRE n.content_hash IS UNIQUE")


def ping() -> bool:
    with _session() as s:
        s.run("RETURN 1").consume()
    return True


# --- Concept canonicalisation -------------------------------------------------
# A concept link only exists if two passages produce the *same* string, so "Fe"
# and "iron" must collapse to one node. The model is asked to normalise, but
# asking is not a guarantee — this map makes the common cases deterministic, and
# is applied both when indexing and when reading a question.
ALIASES = {
    # elements and analytes
    "fe": "iron", "ferrous": "iron", "ferric": "iron", "iron stores": "iron",
    "serum iron": "iron", "elemental iron": "iron",
    "ferritin level": "ferritin", "serum ferritin": "ferritin",
    "25(oh)d": "vitamin d", "25-oh-d": "vitamin d", "25 hydroxyvitamin d": "vitamin d",
    "25-hydroxyvitamin d": "vitamin d", "calcidiol": "vitamin d",
    "cholecalciferol": "vitamin d", "vitamin d3": "vitamin d", "vit d": "vitamin d",
    "b12": "vitamin b12", "cobalamin": "vitamin b12",
    "mg": "magnesium", "zn": "zinc", "i2": "iodine",
    "hb": "haemoglobin", "hgb": "haemoglobin", "hemoglobin": "haemoglobin",
    "crp": "c-reactive protein",
    # thyroid
    "ht": "hashimoto thyroiditis", "hashimoto": "hashimoto thyroiditis",
    "hashimoto's": "hashimoto thyroiditis",
    "hashimoto's thyroiditis": "hashimoto thyroiditis",
    "hashimoto disease": "hashimoto thyroiditis",
    "autoimmune thyroiditis": "autoimmune thyroid disease",
    "aitd": "autoimmune thyroid disease",
    "tsh": "thyroid stimulating hormone", "ft4": "free t4", "t4": "thyroxine",
    "levothyroxine sodium": "levothyroxine", "l-thyroxine": "levothyroxine",
    "tpo antibodies": "thyroid peroxidase antibodies", "anti-tpo": "thyroid peroxidase antibodies",
    # reproductive and metabolic
    "hrt": "hormone replacement therapy", "mht": "hormone replacement therapy",
    "e2": "oestradiol", "estradiol": "oestradiol", "estrogen": "oestrogen",
    "oestrogens": "oestrogen", "progestogen": "progesterone",
    "pcos": "polycystic ovary syndrome", "homa-ir": "insulin resistance",
    "ir": "insulin resistance", "t2dm": "type 2 diabetes",
    "amh": "anti-mullerian hormone", "fsh": "follicle stimulating hormone",
    "bmi": "body mass index", "vte": "venous thromboembolism",
    "dvt": "venous thromboembolism",
    # misc
    "gi": "gastrointestinal", "coeliac": "coeliac disease", "celiac": "coeliac disease",
    "celiac disease": "coeliac disease",
    "tiredness": "fatigue", "exhaustion": "fatigue",
    "hair loss": "hair thinning", "hair shedding": "hair thinning",
    "malabsorption syndrome": "malabsorption",
}


_TARGETS = frozenset(ALIASES.values())
# Endings where a trailing "s" belongs to the word: thyroiditis, diabetes,
# analysis, lupus. Without these the plural rule mangles clinical nouns.
_KEEP_S = ("is", "ss", "us", "es", "sis", "itis", "osis", "asis")


def canon(name: str) -> str:
    """One label per idea: lowercase, de-punctuated, singular, alias-resolved."""
    n = " ".join(str(name).lower().split()).strip(" .,:;()[]").replace("’", "'")
    # Already the canonical form of an alias group — leave it exactly alone.
    if n in _TARGETS:
        return n
    if n in ALIASES:
        return ALIASES[n]
    # Try the possessive-free and plural-free forms before giving up.
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


# --- Duplicate detection ------------------------------------------------------

def content_hash(text: str) -> str:
    """Fingerprint a source body.

    Whitespace is collapsed first so that re-extracting the same PDF, or a
    trailing-newline difference, still fingerprints identically. Anything beyond
    that — an edited sentence, a different edition — is a different source.
    """
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


def find_by_hash(digest: str) -> dict | None:
    with _session() as s:
        rec = s.run(
            "MATCH (src:Source {content_hash: $h}) RETURN src.id AS id",
            h=digest,
        ).single()
    return get_source(rec["id"]) if rec else None


# --- Chunking -----------------------------------------------------------------

def chunk_pages(pages: list[tuple[int | None, str]]) -> list[dict]:
    """Split into passages, carrying the page each one came from.

    `pages` is [(page_number, text), ...] — page_number is None for material with
    no pagination (pasted text, .txt, .md). A passage that straddles a page break
    records both ends, so a citation can say "pages 3-4".
    """
    # Flatten to paragraphs, each remembering its page.
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
        # A single paragraph longer than a passage is split on its own.
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


# --- Ingestion ----------------------------------------------------------------

def ingest_source(
    *, title: str, filename: str, kind: str, origin: str, grade: int,
    summary: str, topics: list[str], passages: list[dict], digest: str,
    body: str, author: str = "", published: str = "", reference: str = "",
    page_count: int = 0, original: tuple[bytes, str, str] | None = None,
) -> dict:
    """Write a read-and-graded source plus its passages.

    The original `body` is stored so the library stays readable — the deck's
    "the original stays readable in the Library" — and because concatenating
    passages back together would double the overlap regions.

    `original` is `(raw_bytes, filename, media_type)` for an uploaded file, or
    None for pasted text. The bytes are archived *after* the Cypher write commits,
    so a duplicate rejected by the source_hash constraint leaves no orphan file.

    Raises neo4j.exceptions.ConstraintError if `digest` is already in the library.
    """
    source_id = str(uuid.uuid4())
    total = len(passages)
    rows = [
        {"id": f"{source_id}:{i}", "text": p["text"], "ordinal": i,
         "page_start": p["page_start"], "page_end": p["page_end"],
         "concepts": canon_all(p.get("concepts"))}
        for i, p in enumerate(passages)
    ]
    with _session() as s:
        s.run(
            """
            CREATE (src:Source {id: $id, title: $title, filename: $filename,
                                kind: $kind, origin: $origin, grade: $grade,
                                summary: $summary, created_at: $now,
                                content_hash: $digest, body: $body,
                                author: $author, published: $published,
                                reference: $reference, page_count: $page_count,
                                char_count: $char_count, passage_count: $total})
            // FOREACH, not UNWIND: UNWIND over an empty list yields zero rows and
            // silently discards the rest of the pipeline, so an untagged source
            // would be written with no passages at all.
            FOREACH (topic IN $topics |
              MERGE (t:Topic {name: topic})
              MERGE (src)-[:TAGGED]->(t))
            FOREACH (row IN $rows |
              CREATE (c:Chunk {id: row.id, text: row.text, ordinal: row.ordinal,
                               page_start: row.page_start, page_end: row.page_end})
              CREATE (src)-[:HAS_CHUNK]->(c)
              // Concepts are the edges that let a passage find related material in
              // other documents; MERGE so the same label is one shared node.
              FOREACH (name IN row.concepts |
                MERGE (k:Concept {name: name})
                MERGE (c)-[:MENTIONS]->(k)))
            """,
            id=source_id, title=title, filename=filename, kind=kind,
            origin=origin, grade=grade, summary=summary, now=_now(),
            topics=topics, rows=rows, digest=digest, body=body,
            author=author, published=published, reference=reference,
            page_count=page_count, char_count=len(body), total=total,
        )
        # Reading-order edges, so a claim split across a boundary can be rejoined.
        s.run(
            """
            MATCH (src:Source {id: $id})-[:HAS_CHUNK]->(c:Chunk)
            WITH c ORDER BY c.ordinal
            WITH collect(c) AS cs
            UNWIND range(0, size(cs) - 2) AS i
              WITH cs[i] AS a, cs[i + 1] AS b
              MERGE (a)-[:NEXT]->(b)
            """,
            id=source_id,
        )
        # Archive the uploaded file last: if the CREATE above hit the uniqueness
        # constraint we never get here, so the store gains no orphan. The node is
        # only told about the file once the bytes are actually on disk.
        if original and originals.save(source_id, original[0], original[1]):
            s.run(
                """
                MATCH (src:Source {id: $id})
                SET src.original_name = $name,
                    src.original_media_type = $media_type,
                    src.original_bytes = $size
                """,
                id=source_id, name=original[1], media_type=original[2],
                size=len(original[0]),
            )
    log("admin", "ingest",
        f"{title} — {total} passages, {page_count or 0} pages, grade {grade}")
    return get_source(source_id)


def link_source(source_id: str, concepts_per_passage: list[list[str]]) -> int:
    """Attach concepts to an already-ingested source. Returns edges written."""
    rows = [{"ordinal": i, "concepts": canon_all(cs)}
            for i, cs in enumerate(concepts_per_passage) if cs]
    if not rows:
        return 0
    with _session() as s:
        s.run(
            """
            UNWIND $rows AS row
            MATCH (src:Source {id: $id})-[:HAS_CHUNK]->(c:Chunk {ordinal: row.ordinal})
            FOREACH (name IN row.concepts |
              MERGE (k:Concept {name: name})
              MERGE (c)-[:MENTIONS]->(k))
            """,
            id=source_id, rows=rows,
        )
        s.run(
            """
            MATCH (src:Source {id: $id})-[:HAS_CHUNK]->(c:Chunk)
            WITH c ORDER BY c.ordinal
            WITH collect(c) AS cs
            UNWIND range(0, size(cs) - 2) AS i
              WITH cs[i] AS a, cs[i + 1] AS b
              MERGE (a)-[:NEXT]->(b)
            """,
            id=source_id,
        )
    return sum(len(r["concepts"]) for r in rows)


def unlinked_sources() -> list[dict]:
    """Sources with no concept edges — ingested before linking, or link failed."""
    with _session() as s:
        recs = s.run(
            """
            MATCH (src:Source)
            WHERE NOT EXISTS { (src)-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(:Concept) }
            RETURN src.id AS id, src.title AS title
            ORDER BY src.created_at
            """
        )
        return [dict(r) for r in recs]


# Every Source field except `body`, which is fetched only by source_text().
_CARD = """
    src.id AS id, src.title AS title, src.filename AS filename,
    src.kind AS kind, src.origin AS origin, src.grade AS grade,
    src.summary AS summary, src.created_at AS created_at,
    src.author AS author, src.published AS published,
    src.reference AS reference, src.page_count AS page_count,
    src.char_count AS char_count, src.content_hash AS content_hash,
    src.original_name AS original_name,
    src.original_media_type AS original_media_type,
    src.original_bytes AS original_bytes
"""


def get_source(source_id: str) -> dict | None:
    with _session() as s:
        rec = s.run(
            f"""
            MATCH (src:Source {{id: $id}})
            OPTIONAL MATCH (src)-[:TAGGED]->(t:Topic)
            OPTIONAL MATCH (src)-[:HAS_CHUNK]->(c:Chunk)
            RETURN {_CARD}, collect(DISTINCT t.name) AS topics,
                   count(DISTINCT c) AS chunks
            """,
            id=source_id,
        ).single()
        if not rec:
            return None
        return {**dict(rec), "topics": sorted(rec["topics"])}


SORTS = {
    "newest": "src.created_at DESC",
    "oldest": "src.created_at ASC",
    "grade_desc": "src.grade DESC, src.title",
    "grade_asc": "src.grade ASC, src.title",
    "title": "toLower(src.title)",
}


def list_sources(search: str = "", topic: str = "", kind: str = "",
                 min_grade: int = 1, max_grade: int = 10,
                 sort: str = "newest", page: int = 1,
                 per_page: int = 10) -> dict:
    """A page of source cards, with search and filters applied.

    Returns the page plus the total match count, so the UI can paginate.
    """
    filters = ["src.grade >= $min_grade", "src.grade <= $max_grade"]
    params: dict = {"min_grade": min_grade, "max_grade": max_grade}
    if search.strip():
        # Includes the full body, not just the card. The AI's summary paraphrases —
        # it wrote "iron absorption" where the source says "ferritin" — so a search
        # limited to title and summary misses sources that plainly discuss the term.
        filters.append(
            "(toLower(src.title) CONTAINS $q OR toLower(src.summary) CONTAINS $q "
            "OR toLower(src.origin) CONTAINS $q OR toLower(src.author) CONTAINS $q "
            # coalesce: sources ingested before the body was stored have none.
            "OR toLower(src.filename) CONTAINS $q "
            "OR toLower(coalesce(src.body, '')) CONTAINS $q)")
        params["q"] = search.strip().lower()
    if kind.strip():
        filters.append("src.kind = $kind")
        params["kind"] = kind.strip()
    if topic.strip():
        filters.append("EXISTS { (src)-[:TAGGED]->(:Topic {name: $topic}) }")
        params["topic"] = topic.strip()

    where = " AND ".join(filters)
    order = SORTS.get(sort, SORTS["newest"])
    page = max(1, page)
    params |= {"skip": (page - 1) * per_page, "limit": per_page}

    with _session() as s:
        total = s.run(
            f"MATCH (src:Source) WHERE {where} RETURN count(src) AS n", **params
        ).single()["n"]
        recs = s.run(
            f"""
            MATCH (src:Source) WHERE {where}
            WITH src ORDER BY {order} SKIP $skip LIMIT $limit
            OPTIONAL MATCH (src)-[:TAGGED]->(t:Topic)
            OPTIONAL MATCH (src)-[:HAS_CHUNK]->(c:Chunk)
            RETURN {_CARD}, collect(DISTINCT t.name) AS topics,
                   count(DISTINCT c) AS chunks
            ORDER BY {order}
            """,
            **params,
        )
        sources = [{**dict(r), "topics": sorted(r["topics"])} for r in recs]

    pages = max(1, (total + per_page - 1) // per_page)
    return {"sources": sources, "total": total, "page": min(page, pages),
            "pages": pages, "per_page": per_page}


def facets() -> dict:
    """The topic and kind values actually present, to populate filter menus."""
    with _session() as s:
        topics = [r["t"] for r in s.run(
            "MATCH (:Source)-[:TAGGED]->(t:Topic) RETURN DISTINCT t.name AS t "
            "ORDER BY t")]
        kinds = [r["k"] for r in s.run(
            "MATCH (src:Source) RETURN DISTINCT src.kind AS k ORDER BY k")]
    return {"topics": topics, "kinds": kinds}


def source_text(source_id: str) -> dict | None:
    """The source as ingested, with its passage boundaries, for reading in the UI."""
    with _session() as s:
        rec = s.run(
            f"MATCH (src:Source {{id: $id}}) RETURN {_CARD}, src.body AS body",
            id=source_id,
        ).single()
        if not rec:
            return None
        passages = s.run(
            """
            MATCH (src:Source {id: $id})-[:HAS_CHUNK]->(c:Chunk)
            RETURN c.ordinal AS ordinal, c.text AS text,
                   c.page_start AS page_start, c.page_end AS page_end
            ORDER BY c.ordinal
            """,
            id=source_id,
        )
        rows = [dict(p) for p in passages]

    card = dict(rec)
    if not card.get("body"):
        # Ingested before the original body was stored. Rebuild a readable
        # version from the passages rather than showing an empty document; the
        # overlap means a sentence may repeat at a boundary, so say so.
        card["body"] = "\n\n".join(p["text"] for p in rows)
        card["body_reconstructed"] = True
    return {**card, "passages": rows}


def set_grade(source_id: str, grade: int) -> dict | None:
    with _session() as s:
        s.run("MATCH (src:Source {id: $id}) SET src.grade = $grade",
              id=source_id, grade=grade)
    log("admin", "regrade", f"{source_id} → grade {grade}")
    return get_source(source_id)


def delete_source(source_id: str) -> None:
    with _session() as s:
        s.run(
            """
            MATCH (src:Source {id: $id})
            OPTIONAL MATCH (src)-[:HAS_CHUNK]->(c:Chunk)
            DETACH DELETE c, src
            """,
            id=source_id,
        )
    # After the node is gone, so a file cannot outlive the source that names it.
    originals.delete(source_id)
    log("admin", "delete", source_id)


# --- Retrieval (the Librarian's shelves) --------------------------------------

def catalogue(min_grade: int) -> list[dict]:
    """The source cards the Librarian is allowed to choose from.

    This is where the grade filter bites: a source below the practitioner's
    grade bar is never even offered, so it cannot reach an answer.
    """
    with _session() as s:
        recs = s.run(
            """
            MATCH (src:Source) WHERE src.grade >= $min_grade
            OPTIONAL MATCH (src)-[:TAGGED]->(t:Topic)
            OPTIONAL MATCH (src)-[:HAS_CHUNK]->(c:Chunk)
            RETURN src.id AS id, src.title AS title, src.summary AS summary,
                   src.grade AS grade, src.origin AS origin, src.kind AS kind,
                   src.author AS author, src.published AS published,
                   collect(DISTINCT t.name) AS topics, count(DISTINCT c) AS passages
            ORDER BY src.grade DESC, src.title
            """,
            min_grade=min_grade,
        )
        return [{**dict(r), "topics": sorted(r["topics"])} for r in recs]


_PASSAGE_FIELDS = """
    c.id AS id, c.text AS text, c.ordinal AS ordinal,
    c.page_start AS page_start, c.page_end AS page_end,
    src.id AS source_id, src.title AS title, src.grade AS grade,
    src.origin AS origin, src.kind AS kind, src.author AS author,
    src.published AS published, src.reference AS reference,
    src.filename AS filename, src.page_count AS page_count,
    src.passage_count AS passage_count
"""


def traverse(seed_source_ids: list[str], min_grade: int,
             focus: list[str] | None = None,
             limit: int | None = None) -> tuple[list[dict], dict]:
    """Walk the corpus outward from the sources the Librarian opened.

    The naive version — take every passage of the opened sources in reading order,
    truncate at the budget — loses anything deep in a long document. A relevant
    paragraph on page 11 of a 40-page protocol simply never arrives. So passages
    are gathered by relevance and connection, not by position:

      `match`    a passage mentioning one of the question's concepts, wherever it
                 sits in the document. This is what reaches page 11.
      `adjacent` the reading-order neighbours of a match, so a claim split across
                 a passage boundary is rejoined and the match keeps its context.
      `linked`   a passage in *another* source sharing >= MIN_SHARED_CONCEPTS with
                 a match — the corpus edge that answers a question from material
                 the Librarian never opened.
      `opened`   whatever budget remains, filled with the rest of the opened
                 sources in reading order, so a short source still arrives whole.

    Every passage is labelled with how it was reached, so the context behind an
    answer is auditable. `min_grade` is enforced at every hop: traversal can never
    smuggle in a source the practitioner excluded.
    """
    limit = limit or cfg.max_passages
    blank = {"match": 0, "adjacent": 0, "linked": 0, "opened": 0,
             "available": 0, "focus": focus or []}
    if not seed_source_ids:
        return [], blank

    # Canonicalise the question's concepts too, or "Fe" would never
    # meet the "iron" node the indexer wrote.
    focus = canon_all(focus)
    picked: dict[str, dict] = {}      # passage id -> passage, first hop wins

    def take(rows, via):
        added = 0
        for r in rows:
            row = dict(r)
            if row["id"] in picked:
                continue
            row["via"] = via
            picked[row["id"]] = row
            added += 1
        return added

    with _session() as s:
        # 1 · concept matches anywhere in the opened sources.
        n_match = take(s.run(
            f"""
            MATCH (src:Source)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(k:Concept)
            WHERE src.id IN $ids AND k.name IN $focus
            WITH c, src, collect(DISTINCT k.name) AS shared
            RETURN {_PASSAGE_FIELDS}, shared
            ORDER BY size(shared) DESC, src.grade DESC, c.ordinal
            LIMIT $limit
            """, ids=seed_source_ids, focus=focus, limit=limit), "match") \
            if focus else 0

        # 2 · neighbours of those matches, for continuity around them.
        n_adj = take(s.run(
            f"""
            MATCH (o:Chunk) WHERE o.id IN $ids
            MATCH (o)-[:NEXT]-(c:Chunk)<-[:HAS_CHUNK]-(src:Source)
            WHERE src.grade >= $min_grade
            RETURN DISTINCT {_PASSAGE_FIELDS}, [] AS shared
            """, ids=list(picked), min_grade=min_grade), "adjacent") \
            if picked else 0

        # 3 · across source boundaries, by shared concepts.
        anchors = list(picked) or None
        n_link = 0
        if anchors:
            n_link = take(s.run(
                f"""
                MATCH (o:Chunk)-[:MENTIONS]->(k:Concept)<-[:MENTIONS]-(c:Chunk)
                MATCH (src:Source)-[:HAS_CHUNK]->(c)
                WHERE o.id IN $anchors AND NOT src.id IN $seeds
                  AND src.grade >= $min_grade
                WITH c, src, collect(DISTINCT k.name) AS shared
                WHERE size(shared) >= $min_shared
                RETURN {_PASSAGE_FIELDS}, shared
                ORDER BY size(shared) DESC, src.grade DESC, c.ordinal
                LIMIT $limit
                """, anchors=anchors, seeds=seed_source_ids, min_grade=min_grade,
                min_shared=cfg.min_shared_concepts, limit=limit), "linked")

        # 4 · fill the remaining budget with the rest of the opened sources.
        n_open = take(s.run(
            f"""
            MATCH (src:Source)-[:HAS_CHUNK]->(c:Chunk)
            WHERE src.id IN $ids
            RETURN {_PASSAGE_FIELDS}, [] AS shared
            ORDER BY src.grade DESC, src.title, c.ordinal
            """, ids=seed_source_ids), "opened")

    rank = {"match": 0, "adjacent": 1, "linked": 2, "opened": 3}
    ordered = sorted(
        picked.values(),
        key=lambda p: (rank[p["via"]], -len(p.get("shared") or []),
                       p["title"], p["ordinal"]),
    )
    kept = ordered[:limit]
    # Within the prompt, reading order is easier for the model to follow than
    # relevance order, so re-sort what survived the budget.
    kept.sort(key=lambda p: (p["title"], p["ordinal"]))
    stats = {"match": n_match, "adjacent": n_adj, "linked": n_link,
             "opened": n_open, "available": len(ordered), "focus": focus}
    return kept, stats


def concepts_for(source_id: str, limit: int = 40) -> list[str]:
    with _session() as s:
        return [r["n"] for r in s.run(
            """
            MATCH (:Source {id: $id})-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(k:Concept)
            RETURN k.name AS n, count(*) AS uses
            ORDER BY uses DESC, n LIMIT $limit
            """, id=source_id, limit=limit)]


def neighbours_of(source_id: str, limit: int = 6) -> list[dict]:
    """Other sources connected to this one, and the concepts they share."""
    with _session() as s:
        recs = s.run(
            """
            MATCH (:Source {id: $id})-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(k:Concept)
                  <-[:MENTIONS]-(:Chunk)<-[:HAS_CHUNK]-(other:Source)
            WHERE other.id <> $id
            WITH other, collect(DISTINCT k.name) AS shared
            RETURN other.id AS id, other.title AS title, other.grade AS grade,
                   shared, size(shared) AS n
            ORDER BY n DESC, other.grade DESC LIMIT $limit
            """, id=source_id, limit=limit)
        return [dict(r) for r in recs]


def all_concepts() -> list[str]:
    with _session() as s:
        return [r["n"] for r in s.run(
            "MATCH (k:Concept) RETURN k.name AS n ORDER BY n")]


def all_topics() -> list[str]:
    with _session() as s:
        return [r["n"] for r in s.run(
            "MATCH (t:Topic) RETURN t.name AS n ORDER BY n")]


def merge_nodes(label: str, groups: list[dict]) -> int:
    """Fold alias nodes into their canonical node, moving the edges with them.

    `label` is 'Concept' or 'Topic'. Returns how many nodes were absorbed.
    """
    rel = "MENTIONS" if label == "Concept" else "TAGGED"
    merged = 0
    with _session() as s:
        for g in groups:
            res = s.run(
                f"""
                MERGE (keep:{label} {{name: $canonical}})
                WITH keep
                UNWIND $aliases AS alias
                MATCH (drop:{label} {{name: alias}})
                WHERE drop <> keep
                // Re-point every edge at the surviving node, then remove the alias.
                CALL (drop, keep) {{
                  MATCH (n)-[:{rel}]->(drop)
                  MERGE (n)-[:{rel}]->(keep)
                }}
                DETACH DELETE drop
                RETURN count(*) AS n
                """,
                canonical=g["canonical"], aliases=g["aliases"],
            ).single()
            merged += res["n"] if res else 0
    return merged


def graph_stats() -> dict:
    with _session() as s:
        rec = s.run(
            """
            CALL () { MATCH (k:Concept) RETURN count(k) AS concepts }
            CALL () { MATCH (:Chunk)-[m:MENTIONS]->(:Concept) RETURN count(m) AS mentions }
            CALL () { MATCH (:Chunk)-[n:NEXT]->(:Chunk) RETURN count(n) AS order_edges }
            CALL () {
              MATCH (a:Source)-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(:Concept)
                    <-[:MENTIONS]-(:Chunk)<-[:HAS_CHUNK]-(b:Source)
              WHERE elementId(a) < elementId(b)
              RETURN count(DISTINCT [elementId(a), elementId(b)]) AS source_links
            }
            RETURN concepts, mentions, order_edges, source_links
            """
        ).single()
        return dict(rec)


def passages_for(source_ids: list[str], limit: int | None = None) -> tuple[list[dict], int]:
    """Every passage of the chosen sources, in reading order.

    Returns (passages, total_available) so a caller can tell the practitioner
    when the limit truncated the material rather than silently dropping it.
    """
    limit = limit or cfg.max_passages
    if not source_ids:
        return [], 0
    with _session() as s:
        total = s.run(
            "MATCH (src:Source)-[:HAS_CHUNK]->(c:Chunk) WHERE src.id IN $ids "
            "RETURN count(c) AS n",
            ids=source_ids,
        ).single()["n"]
        recs = s.run(
            """
            MATCH (src:Source)-[:HAS_CHUNK]->(c:Chunk)
            WHERE src.id IN $ids
            RETURN c.id AS id, c.text AS text, c.ordinal AS ordinal,
                   c.page_start AS page_start, c.page_end AS page_end,
                   src.id AS source_id, src.title AS title, src.grade AS grade,
                   src.origin AS origin, src.kind AS kind, src.author AS author,
                   src.published AS published, src.reference AS reference,
                   src.filename AS filename, src.page_count AS page_count,
                   src.passage_count AS passage_count
            ORDER BY src.grade DESC, src.title, c.ordinal
            LIMIT $limit
            """,
            ids=source_ids, limit=limit,
        )
        return [dict(r) for r in recs], total


# --- Coverage & audit ---------------------------------------------------------

def coverage() -> list[dict]:
    with _session() as s:
        recs = s.run(
            """
            MATCH (t:Topic)<-[:TAGGED]-(src:Source)
            OPTIONAL MATCH (src)-[:HAS_CHUNK]->(c:Chunk)
            RETURN t.name AS topic, count(DISTINCT src) AS sources,
                   count(DISTINCT c) AS chunks
            ORDER BY chunks DESC, topic
            """
        )
        return [dict(r) for r in recs]


def log(actor: str, action: str, detail: str) -> None:
    """Record a library event.

    Library events only — anything that names a patient or quotes a clinical
    question goes to patients.log() so it stays inside the patient vault.
    """
    with _session() as s:
        s.run(
            "CREATE (:AuditEvent {id: $id, ts: $ts, actor: $actor, "
            "action: $action, detail: $detail})",
            id=str(uuid.uuid4()), ts=_now(), actor=actor, action=action,
            detail=detail,
        )


def audit(limit: int = 100) -> list[dict]:
    with _session() as s:
        recs = s.run(
            "MATCH (e:AuditEvent) RETURN e ORDER BY e.ts DESC LIMIT $limit",
            limit=limit,
        )
        return [{**dict(r["e"]), "vault": "library"} for r in recs]


def stats() -> dict:
    with _session() as s:
        rec = s.run(
            """
            CALL () { MATCH (s:Source) RETURN count(s) AS sources }
            CALL () { MATCH (c:Chunk) RETURN count(c) AS chunks }
            CALL () { MATCH (t:Topic) RETURN count(t) AS topics }
            RETURN sources, chunks, topics
            """
        ).single()
        return dict(rec)
