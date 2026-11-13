"""pgvector-backed chunk store for the "general lookup" fast RAG path —
one Postgres vector-similarity query, no graph traversal, no Neo4j
round-trip at all. This exists *alongside* app/retrieval/traversal.py's
graph-traversal path ("deep research"), not in place of it — a
practitioner picks per-question which they want (app/main.py's
MeConsult.retrieval_mode).

Chunks are duplicated here at ingest time (app/main.py's _ingest_pages,
right after the existing Neo4j write), not looked up from Neo4j on
query — the whole point of this path is staying out of Neo4j entirely,
so document_title/grade/page span are copied in alongside the text and
embedding rather than joined at query time.
"""
from __future__ import annotations

from ..config import get_config
from ..db import core_connection

cfg = get_config()


def _vec_literal(embedding: list[float]) -> str:
    # psycopg2 has no built-in adapter for pgvector's `vector` type (that
    # needs the separate `pgvector` package's register_vector()) — a
    # plain bound string parameter cast with ::vector in the SQL text
    # avoids that extra dependency for what's otherwise one line.
    return "[" + ",".join(str(x) for x in embedding) + "]"


def ensure_schema() -> None:
    """Create the pgvector extension + table. Idempotent — safe on boot,
    same pattern as core_store.ensure_schema()/graph.schema.ensure_schema()."""
    with core_connection() as conn:
        conn.executescript("CREATE EXTENSION IF NOT EXISTS vector")
        # cfg.embedding_dimensions must match the Embedder's real output
        # size, same constraint app/graph/schema.py's Neo4j vector index
        # has — a mismatch fails loudly here too, not silently.
        conn.executescript(f"""
            CREATE TABLE IF NOT EXISTS chunk_embeddings (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                document_title TEXT NOT NULL,
                grade INTEGER NOT NULL,
                text TEXT NOT NULL,
                page_start INTEGER,
                page_end INTEGER,
                embedding vector({cfg.embedding_dimensions}) NOT NULL
            )
        """)
        # CREATE TABLE IF NOT EXISTS above is a no-op for a table that
        # already existed before is_private was added (specs/v6.9/01) —
        # found live, same gap core_store.py's practitioners table hit
        # for can_upload_library: apply it explicitly too, or this column
        # silently never exists on a database that predates it and every
        # set_private() call 500s with UndefinedColumn.
        conn.executescript(
            "ALTER TABLE chunk_embeddings ADD COLUMN IF NOT EXISTS "
            "is_private BOOLEAN NOT NULL DEFAULT FALSE"
        )
        # Same migration pattern, for the library scope (folder/tag) hard
        # filter general_lookup() now honors too, mirroring the Neo4j
        # Document.folder_path/topics this table otherwise has no copy
        # of (see search()'s and save_chunk_embeddings()'s docstrings).
        conn.executescript(
            "ALTER TABLE chunk_embeddings ADD COLUMN IF NOT EXISTS "
            "folder_path TEXT NOT NULL DEFAULT ''"
        )
        conn.executescript(
            "ALTER TABLE chunk_embeddings ADD COLUMN IF NOT EXISTS "
            "topics TEXT[] NOT NULL DEFAULT '{}'"
        )


def save_chunk_embeddings(document_id: str, document_title: str, grade: int,
                          chunks: list[dict], folder_path: str = "",
                          topics: list[str] | None = None) -> None:
    """`chunks` is [{"id", "text", "embedding", "page_start", "page_end"}, ...]
    — the same passage dicts the Neo4j write already uses. Called right
    alongside that write (not instead of it) so both stores stay in sync;
    upserts so a regrade/re-ingest updates rather than duplicates.

    `folder_path`/`topics` are copied in the same way grade is — this
    table has no live join back to Neo4j's Document, so a folder/tag
    scope chosen for this path (search() below) needs its own copy here,
    kept in sync by this call and by update_metadata() below."""
    if not chunks:
        return
    topics = topics or []
    with core_connection() as conn:
        for c in chunks:
            if c.get("embedding") is None:
                continue
            conn.execute(
                """
                INSERT INTO chunk_embeddings
                    (chunk_id, document_id, document_title, grade, text, page_start, page_end,
                     embedding, folder_path, topics)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    document_title = EXCLUDED.document_title,
                    grade = EXCLUDED.grade,
                    text = EXCLUDED.text,
                    page_start = EXCLUDED.page_start,
                    page_end = EXCLUDED.page_end,
                    embedding = EXCLUDED.embedding,
                    folder_path = EXCLUDED.folder_path,
                    topics = EXCLUDED.topics
                """,
                (c["id"], document_id, document_title, grade, c["text"],
                 c.get("page_start"), c.get("page_end"), _vec_literal(c["embedding"]),
                 folder_path, topics),
            )


def update_metadata(document_id: str, folder_path: str, topics: list[str]) -> None:
    """Mirrors store.set_folder()/set_topics() on the Neo4j side — called
    from the same admin PATCH endpoints so this table's copy of
    folder_path/topics (save_chunk_embeddings' docstring) doesn't drift
    out of sync with the source of truth after a re-placement/re-tag."""
    with core_connection() as conn:
        conn.execute(
            "UPDATE chunk_embeddings SET folder_path = %s, topics = %s WHERE document_id = %s",
            (folder_path, topics, document_id),
        )


def delete_document(document_id: str) -> None:
    """Mirrors store.delete_document() on the Neo4j side — called from
    the same place so a removed source disappears from both retrieval
    paths, not just one."""
    with core_connection() as conn:
        conn.execute("DELETE FROM chunk_embeddings WHERE document_id = %s", (document_id,))


def set_private(document_ids: list[str], is_private: bool) -> None:
    """Mirrors store.set_private()/set_folder_private() on the Neo4j
    side (specs/v6.9/01) — this table has no folder_path of its own, so
    a "privatize this folder" bulk action passes the document ids Neo4j
    already resolved rather than this store re-deriving the match."""
    if not document_ids:
        return
    with core_connection() as conn:
        conn.execute(
            "UPDATE chunk_embeddings SET is_private = %s WHERE document_id = ANY(%s)",
            (is_private, document_ids),
        )


def search(query_embedding: list[float], top_k: int, min_grade: int,
          accessible_private_ids: set[str] | None = None,
          folder: str = "", topic: str = "") -> list[dict]:
    """Exact nearest-neighbor search (cosine distance) — no ANN index.
    The library is small enough today that a sequential scan over
    chunk_embeddings is fast on its own; an ivfflat/hnsw index is the
    obvious next step if the corpus grows large enough for this to
    start costing real time, not added preemptively.

    `accessible_private_ids` gates a private document out of this fast
    path the same way the deep-research path's seed search and every
    traversal hop already are (specs/v6.9/01) — this path has no
    weight-aware grade check of its own either (a pre-existing gap, not
    introduced here), so the privacy gate is a plain SQL filter, same
    as the `grade >= %s` check already is.

    `folder`/`topic` is the same hard library-scope filter the
    deep-research path enforces via store.in_scope() — this path has no
    traversal hops to re-check it at, so it only needs applying here,
    at the one query this path makes."""
    accessible_private_ids = accessible_private_ids or set()
    filters = ["grade >= %s", "(NOT is_private OR document_id = ANY(%s))"]
    params: list = [min_grade, list(accessible_private_ids)]
    if folder:
        # starts_with(), not LIKE — a folder name containing '_' or '%'
        # (both valid in the Neo4j-side folder_path string) would
        # otherwise be interpreted as a LIKE wildcard instead of a
        # literal prefix.
        filters.append("(folder_path = %s OR starts_with(folder_path, %s))")
        params += [folder, f"{folder}/"]
    if topic:
        filters.append("%s = ANY(topics)")
        params.append(topic)
    where = " AND ".join(filters)
    with core_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT chunk_id AS id, document_id, document_title, grade, text,
                   page_start, page_end,
                   1 - (embedding <=> %s::vector) AS score
            FROM chunk_embeddings
            WHERE {where}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            [_vec_literal(query_embedding), *params, _vec_literal(query_embedding), top_k],
        ).fetchall()
        return [dict(r) for r in rows]


def count() -> int:
    with core_connection() as conn:
        row = conn.execute("SELECT count(*) AS n FROM chunk_embeddings").fetchone()
        return row["n"]
