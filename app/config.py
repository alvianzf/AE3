"""Environment-driven configuration for the clinic platform PoC."""
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Config:
    # "production" enforces the fail-closed checks in get_config() below.
    # Any other value (default) keeps the dev-friendly fallbacks.
    env = os.getenv("ENV", "development")

    # Neo4j — the knowledge library
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "graphrag-poc")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

    # Filesystem — uploaded files, kept byte-for-byte alongside the chunks
    originals_path = os.getenv("ORIGINALS_PATH", "data/originals")

    # Postgres — replaces the old per-file SQLite stores (specs/v6). The
    # core store lives in the `public` schema; each Pro practitioner's
    # vault gets its own schema (vault_<id>), created on Pro activation —
    # same physical database, isolation preserved via schema instead of
    # a separate file. See app/db.py.
    postgres_host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    postgres_port = int(os.getenv("POSTGRES_PORT", "5433"))
    postgres_user = os.getenv("POSTGRES_USER", "postgres")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "")
    postgres_database = os.getenv("POSTGRES_DATABASE", "clinic")
    postgres_pool_max = int(os.getenv("POSTGRES_POOL_MAX", "20"))
    # Pre-migration SQLite paths — no longer read by core_store.py/vault.py
    # themselves, kept only as scripts/migrate_sqlite_to_postgres.py's
    # source-data locations.
    core_db_path = os.getenv("CORE_DB_PATH", "data/core.db")
    vaults_path = os.getenv("VAULTS_PATH", "data/vaults")
    # A Pro practitioner's uploaded client files, id-not-filename, one
    # directory per practitioner underneath this.
    vault_files_path = os.getenv("VAULT_FILES_PATH", "data/vault-files")
    # Practitioner profile photos — public, served directly (unlike the
    # private originals/vault-files stores above).
    photos_path = os.getenv("PHOTOS_PATH", "data/photos")
    # Staging area for chunked uploads (app/uploads.py) — a large file is
    # written here piece by piece as its chunks arrive, so the process
    # never holds more than one chunk in memory at once. Swept for
    # abandoned uploads older than a day.
    upload_staging_path = os.getenv("UPLOAD_STAGING_PATH", "data/upload-staging")
    # 200 MB: the largest source document or client file this app accepts.
    # Enforced at chunked-upload init, before any bytes are received.
    max_upload_bytes = int(os.getenv("MAX_UPLOAD_BYTES", str(200 * 1024 * 1024)))

    # Nebius token factory — OpenAI-compatible (specs/v4.2). One shared
    # server-side key for every practitioner; the earlier per-practitioner
    # BYO-Anthropic-key model is retired, not renamed.
    nebius_api_key = os.getenv("NEBIUS_API_KEY", "")
    nebius_base_url = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")

    # The AI team — six roles now, not four (specs/v4.2/01). Defaults below
    # are the human-readable model names as given when this was specced;
    # **confirm each one against Nebius's actual catalog ID** before relying
    # on these defaults (specs/v4.2/01 flags this as unverified — the
    # catalog's real `model=` strings are typically namespaced, e.g.
    # "Qwen/Qwen3-32B", not the bare label used here).
    reader_model = os.getenv("READER_MODEL", "Qwen3.6-27B")
    graph_builder_model = os.getenv("GRAPH_BUILDER_MODEL", "MedGemma-27B")
    embedder_model = os.getenv("EMBEDDER_MODEL", "Qwen3-Embedding-8B")
    retrieval_model = os.getenv("RETRIEVAL_MODEL", "Qwen3-8B")
    reasoner_model = os.getenv("REASONER_MODEL", "KIMI-K3")

    # Per-role base_url/api_key overrides (app/clients/llm_client.py). Every
    # role defaults to the shared Nebius endpoint above — set a role's own
    # <ROLE>_BASE_URL/<ROLE>_API_KEY only when that specific role actually
    # needs to move to a different provider/deployment. Never hardcode a
    # base_url in business logic; this is the one place it's read from.
    reader_base_url = os.getenv("READER_BASE_URL", nebius_base_url)
    reader_api_key = os.getenv("READER_API_KEY", nebius_api_key)
    graph_builder_base_url = os.getenv("GRAPH_BUILDER_BASE_URL", nebius_base_url)
    graph_builder_api_key = os.getenv("GRAPH_BUILDER_API_KEY", nebius_api_key)
    embedder_base_url = os.getenv("EMBEDDER_BASE_URL", nebius_base_url)
    embedder_api_key = os.getenv("EMBEDDER_API_KEY", nebius_api_key)
    retrieval_base_url = os.getenv("RETRIEVAL_BASE_URL", nebius_base_url)
    retrieval_api_key = os.getenv("RETRIEVAL_API_KEY", nebius_api_key)
    reasoner_base_url = os.getenv("REASONER_BASE_URL", nebius_base_url)
    reasoner_api_key = os.getenv("REASONER_API_KEY", nebius_api_key)
    # Not a chat model — a hallucination-detection classifier run directly
    # via transformers, not through the Nebius chat endpoint. Default is
    # HHEM-2.1-Open's real Hugging Face repo id, not a Nebius catalog name.
    checker_model = os.getenv("CHECKER_MODEL", "vectara/hallucination_evaluation_model")
    # Threshold below which a (claim, evidence) pair is flagged as
    # unsupported — HHEM's score is a 0-1 consistency probability, higher
    # is more supported. Not calibrated against real examples yet
    # (specs/v4.2/01) — a starting value, not a validated one.
    checker_threshold = float(os.getenv("CHECKER_THRESHOLD", "0.5"))
    # Qwen3-Embedding-8B's real output dimension is unconfirmed here
    # (specs/v4.2/01) — must match whatever the model actually returns or
    # the Neo4j vector index creation below fails outright, loudly, not
    # silently: confirm this value before deploying.
    embedding_dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "4096"))

    # Ingestion — passages are the citable unit
    chunk_size = int(os.getenv("CHUNK_SIZE", "1200"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "150"))

    # Signs the session cookie (app/auth.py). Set a random value per deployment.
    session_secret = os.getenv("SESSION_SECRET", "dev-only-not-secret")
    # Off for local http development, on behind TLS.
    cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"

    # The first admin account, created on boot if the admins table is empty
    # and both are set. Unset in production once an admin exists — it's a
    # one-time bootstrap, not a standing credential to leave configured.
    admin_bootstrap_email = os.getenv("ADMIN_BOOTSTRAP_EMAIL", "")
    admin_bootstrap_password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "")

    # Stripe — practitioner Pro plan billing (specs/v2/09-payments.md)
    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_price_id_pro = os.getenv("STRIPE_PRICE_ID_PRO", "")

    # Wearable OAuth connect — v2 seeds fixture data after connecting, it does
    # not pull live vendor data (specs/v2/06-client-portal.md).
    oura_client_id = os.getenv("OURA_CLIENT_ID", "")
    oura_client_secret = os.getenv("OURA_CLIENT_SECRET", "")
    whoop_client_id = os.getenv("WHOOP_CLIENT_ID", "")
    whoop_client_secret = os.getenv("WHOOP_CLIENT_SECRET", "")
    garmin_client_id = os.getenv("GARMIN_CLIENT_ID", "")
    garmin_client_secret = os.getenv("GARMIN_CLIENT_SECRET", "")
    # Base URL this app is served at, needed to build OAuth redirect_uris.
    public_base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

    # Retrieval — the grade threshold below which a Document (or, in a
    # traversal hop, its Chunk) is invisible to the graph-traversal
    # retriever (app/retrieval/), same threshold a practitioner's own
    # per-source weight can override upward or downward (app/vault.py's
    # source_weights, threaded through as `weights` in retrieval/).
    min_grade = int(os.getenv("MIN_GRADE", "7"))

    # Graph-traversal retrieval (app/retrieval/). A circuit breaker against
    # runaway cost/depth, not the primary stopping logic — the primary
    # stop is the frontier actually going empty (every branch pruned).
    traversal_max_depth = int(os.getenv("TRAVERSAL_MAX_DEPTH", "5"))
    # Candidates fetched per hop, before LLM judgment — bounds one hop's
    # Cypher result size and the batch size of the per-hop relevance call.
    traversal_max_candidates_per_hop = int(os.getenv("TRAVERSAL_MAX_CANDIDATES_PER_HOP", "20"))
    # Seed chunks pulled by the initial vector (+ full-text) search, before
    # traversal ever starts expanding.
    traversal_seed_top_k = int(os.getenv("TRAVERSAL_SEED_TOP_K", "10"))


@lru_cache
def get_config() -> Config:
    cfg = Config()
    if cfg.env == "production":
        if cfg.session_secret in ("", "dev-only-not-secret"):
            raise RuntimeError(
                "SESSION_SECRET must be set to a real value when ENV=production"
            )
        if cfg.neo4j_password in ("", "graphrag-poc"):
            raise RuntimeError(
                "NEO4J_PASSWORD must be set to a real value when ENV=production"
            )
        if not cfg.nebius_api_key:
            raise RuntimeError(
                "NEBIUS_API_KEY must be set to a real value when ENV=production"
            )
    return cfg
