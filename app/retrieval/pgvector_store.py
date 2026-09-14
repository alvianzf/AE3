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


def save_chunk_embeddings(document_id: str, document_title: str, grade: int,
                          chunks: list[dict]) -> None:
    """`chunks` is [{"id", "text", "embedding", "page_start", "page_end"}, ...]
    — the same passage dicts the Neo4j write already uses. Called right
    alongside that write (not instead of it) so both stores stay in sync;
    upserts so a regrade/re-ingest updates rather than duplicates."""
    if not chunks:
        return
    with core_connection() as conn:
        for c in chunks:
            if c.get("embedding") is None:
                continue
            conn.execute(
                """
                INSERT INTO chunk_embeddings
                    (chunk_id, document_id, document_title, grade, text, page_start, page_end, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    document_title = EXCLUDED.document_title,
                    grade = EXCLUDED.grade,
                    text = EXCLUDED.text,
                    page_start = EXCLUDED.page_start,
                    page_end = EXCLUDED.page_end,
                    embedding = EXCLUDED.embedding
                """,
                (c["id"], document_id, document_title, grade, c["text"],
                 c.get("page_start"), c.get("page_end"), _vec_literal(c["embedding"])),
            )


def delete_document(document_id: str) -> None:
    """Mirrors store.delete_document() on the Neo4j side — called from
    the same place so a removed source disappears from both retrieval
    paths, not just one."""
    with core_connection() as conn:
        conn.execute("DELETE FROM chunk_embeddings WHERE document_id = %s", (document_id,))


def search(query_embedding: list[float], top_k: int, min_grade: int) -> list[dict]:
    """Exact nearest-neighbor search (cosine distance) — no ANN index.
    The library is small enough today that a sequential scan over
    chunk_embeddings is fast on its own; an ivfflat/hnsw index is the
    obvious next step if the corpus grows large enough for this to
    start costing real time, not added preemptively."""
    with core_connection() as conn:
        rows = conn.execute(
            """
            SELECT chunk_id AS id, document_id, document_title, grade, text,
                   page_start, page_end,
                   1 - (embedding <=> %s::vector) AS score
            FROM chunk_embeddings
            WHERE grade >= %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (_vec_literal(query_embedding), min_grade, _vec_literal(query_embedding), top_k),
        ).fetchall()
        return [dict(r) for r in rows]


def count() -> int:
    with core_connection() as conn:
        row = conn.execute("SELECT count(*) AS n FROM chunk_embeddings").fetchone()
        return row["n"]
