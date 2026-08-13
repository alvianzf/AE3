"""Environment-driven configuration for the clinic platform PoC."""
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Config:
    # Neo4j — the knowledge library
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "graphrag-poc")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

    # Filesystem — uploaded files, kept byte-for-byte alongside the chunks
    originals_path = os.getenv("ORIGINALS_PATH", "data/originals")

    # SQLite — the core store: practitioners, plans, contact forms,
    # questionnaires, site stats. Shared, cross-tenant by nature.
    core_db_path = os.getenv("CORE_DB_PATH", "data/core.db")
    # One SQLite file per Pro practitioner, created on Pro activation.
    vaults_path = os.getenv("VAULTS_PATH", "data/vaults")
    # A Pro practitioner's uploaded client files, id-not-filename, one
    # directory per practitioner underneath this.
    vault_files_path = os.getenv("VAULT_FILES_PATH", "data/vault-files")
    # Encrypts a practitioner's own Anthropic API key at rest (Fernet).
    # Must be set to a real generated key in any deployment that stores one.
    vault_encryption_key = os.getenv("VAULT_ENCRYPTION_KEY", "")
    # Practitioner profile photos — public, served directly (unlike the
    # private originals/vault-files stores above).
    photos_path = os.getenv("PHOTOS_PATH", "data/photos")

    # The AI team (one model per role)
    reader_model = os.getenv("READER_MODEL", "claude-haiku-4-5")
    # Sonnet, not Haiku: Haiku 4.5 refuses to open a low-graded source even when
    # the practitioner has explicitly allowed it in, which silently breaks the
    # grade slider. Sonnet 5 separates relevance from reliability as instructed.
    librarian_model = os.getenv("LIBRARIAN_MODEL", "claude-sonnet-5")
    answer_model = os.getenv("ANSWER_MODEL", "claude-opus-5")
    checker_model = os.getenv("CHECKER_MODEL", "claude-haiku-4-5")

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

    # Retrieval
    min_grade = int(os.getenv("MIN_GRADE", "7"))
    # How many sources the Librarian may open at once, and how many passages
    # those sources may contribute. Both are ceilings, not targets — the API
    # reports when either one truncated the material.
    #
    # max_sources is effectively "no limit" at PoC scale: the Librarian's own
    # relevance judgement is the real filter, and capping it would silently drop
    # sources it deliberately chose. max_passages is the binding constraint that
    # keeps the Specialist's prompt bounded.
    max_sources = int(os.getenv("MAX_SOURCES", "100"))
    max_passages = int(os.getenv("MAX_PASSAGES", "120"))
    # How many concepts two passages must share before the graph treats them as
    # related. 1 is too loose ("vitamin d" alone links almost everything); 2 keeps
    # a link meaningful without needing embeddings.
    min_shared_concepts = int(os.getenv("MIN_SHARED_CONCEPTS", "2"))


@lru_cache
def get_config() -> Config:
    return Config()
