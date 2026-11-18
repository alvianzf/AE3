"""Neo4j schema for the graph-traversal knowledge base (see the module
docstring in store.py for the full node/relationship shape and why this
replaces the old Source/Chunk/Topic/Concept schema)."""
from __future__ import annotations

from ..config import get_config
from .driver import session

cfg = get_config()


def ensure_schema() -> None:
    """Create constraints and indexes. Idempotent — safe to call on boot."""
    with session() as s:
        s.run("CREATE CONSTRAINT document_id IF NOT EXISTS "
              "FOR (n:Document) REQUIRE n.id IS UNIQUE")
        s.run("CREATE CONSTRAINT chunk_id IF NOT EXISTS "
              "FOR (n:Chunk) REQUIRE n.id IS UNIQUE")
        s.run("CREATE CONSTRAINT entity_id IF NOT EXISTS "
              "FOR (n:Entity) REQUIRE n.id IS UNIQUE")
        # Entity resolution key (store.py's upsert_entity) — see that
        # function's docstring for what "basic" means here and the TODO
        # on smarter resolution.
        s.run("CREATE CONSTRAINT entity_name IF NOT EXISTS "
              "FOR (n:Entity) REQUIRE n.name IS UNIQUE")
        # A duplicate ingest fails at the database, not just the
        # read-then-write check in ingestion/pipeline.py, which two
        # concurrent uploads could both pass.
        s.run("CREATE CONSTRAINT document_hash IF NOT EXISTS "
              "FOR (n:Document) REQUIRE n.content_hash IS UNIQUE")
        # A folder with no documents in it yet (specs/v6.8/01's known
        # limitation, closed here) — Document.folder_path alone can't
        # represent a folder an admin created ahead of uploading anything
        # into it, so an explicitly-created folder gets a real node.
        # Documents filed into a path with no :Folder node still work
        # exactly as before (store.facets()/the folder tree treat a
        # folder as "real" either way — a Document-implied path or an
        # explicit :Folder, unioned).
        s.run("CREATE CONSTRAINT folder_path IF NOT EXISTS "
              "FOR (n:Folder) REQUIRE n.path IS UNIQUE")
        # Registers the owner_practitioner_id property-key token up front
        # (specs/v6.9/01's private-document ownership) — without this,
        # Neo4j logs "property key does not exist" on every query that
        # reads it (store.py's _CARD) until the first private document is
        # ever ingested, since a null property value is never stored and
        # the token otherwise doesn't exist until then. Confirmed live:
        # the feature itself works end-to-end (ingest_document sets it,
        # get_document/delete_own_source/promote_own_staged read it back
        # correctly) — this is just to silence the noise, not a
        # functional fix.
        s.run("CREATE INDEX document_owner_practitioner_id IF NOT EXISTS "
              "FOR (n:Document) ON (n.owner_practitioner_id)")

        # Vector index for seed search (retrieval/seed_search.py).
        # cfg.embedding_dimensions must match Qwen3-Embedding-8B's real
        # output size or this fails outright — see config.py's comment.
        s.run(
            "CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS "
            "FOR (c:Chunk) ON (c.embedding) "
            "OPTIONS {indexConfig: {"
            "`vector.dimensions`: $dims, "
            "`vector.similarity_function`: 'cosine'}}",
            dims=cfg.embedding_dimensions,
        )

        # Full-text indexes: entity-name lookup for seed search's entity
        # seeds, and chunk-text lookup as the "+ optionally full-text"
        # complement to vector seed search.
        s.run(
            "CREATE FULLTEXT INDEX entity_name_fulltext IF NOT EXISTS "
            "FOR (n:Entity) ON EACH [n.name]"
        )
        s.run(
            "CREATE FULLTEXT INDEX chunk_text_fulltext IF NOT EXISTS "
            "FOR (n:Chunk) ON EACH [n.text]"
        )


def ping() -> bool:
    with session() as s:
        s.run("RETURN 1").consume()
    return True
