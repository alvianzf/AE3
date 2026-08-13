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

    # SQLite — the patient vault (v1) / a single practitioner's vault (v2)
    sqlite_path = os.getenv("SQLITE_PATH", "data/patients.db")

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

    # Access gate — a shared door code, not user authentication. See app/gate.py.
    access_passphrase = os.getenv("ACCESS_PASSPHRASE", "DevshorePartners2026")
    # Signs the access cookie. Set a random value per deployment; if it changes,
    # everyone is simply asked for the phrase again.
    session_secret = os.getenv("SESSION_SECRET", "dev-only-not-secret")
    # Off for local http development, on behind TLS.
    cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"

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
