"""A pooled, de-identified library of clinical patterns extracted from
finalized consult documents across every practitioner — "when X finding
appears, practitioners typically recommend Y" — fed back into future
consults/document drafts as extra grounding (app/reasoning/reasoner.py),
so the system's answers improve the more real consultations it sees,
without ever retaining anything that identifies a client or practitioner.

De-identification is safety-critical here (this pool is shared across
the whole platform, not scoped to one practitioner's own vault), so
extraction always routes to Claude directly, the same override pattern
app/ingestion/ocr.py and app/pdf_tidy.py use regardless of the live
provider toggle — this is the one call in the pipeline where getting it
wrong has real consequences, not a place to follow a superadmin's
general-purpose model preference.
"""
from __future__ import annotations

from . import core_store
from .clients.anthropic_client import AnthropicLLMClient
from .clients.llm_client import Role, _ANTHROPIC_MODELS
from .clients.llm_client import get_client as get_llm_client
from .config import get_config

cfg = get_config()

EXTRACTION_SYSTEM = (
    "You extract generalizable clinical patterns from a finalized "
    "practitioner document (a clinician note or a client report) for a "
    "shared, de-identified pattern library used to help with FUTURE, "
    "unrelated consultations. This library is pooled across many "
    "practitioners and many clients, so what you extract must NEVER be "
    "traceable back to the person this document was actually about.\n\n"
    "For each distinct clinical finding-to-recommendation pairing in the "
    "document, extract:\n"
    "- topic: a short category (e.g. \"Progesterone\", \"Sleep and "
    "cortisol\", \"Insulin resistance\")\n"
    "- finding: the generalized clinical pattern observed, written as a "
    "fact about the finding itself, not about this specific person "
    "(e.g. \"Low progesterone metabolites with normal metabolism\", not "
    "\"The client's progesterone was low\")\n"
    "- recommendation: the generalized action taken for that finding "
    "(e.g. \"Trial bio-identical progesterone supplementation\", not "
    "\"We agreed you'd start 100mg daily\")\n\n"
    "Strict rules:\n"
    "- NEVER include a name, age, date, location, contact detail, "
    "session date, or any other identifying detail.\n"
    "- NEVER include an exact dose, lab value, or quote specific enough "
    "to re-identify the person it came from — generalize it (\"low\", "
    "\"elevated\", \"within normal range\") rather than restate the exact "
    "number.\n"
    "- Only extract patterns with real clinical substance — skip "
    "pleasantries, scheduling, and anything with no finding or no "
    "recommendation attached.\n"
    "- If the document has no extractable clinical pattern at all, "
    "return an empty list."
)

_PATTERN_SCHEMA = {
    "type": "object",
    "properties": {
        "patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "finding": {"type": "string"},
                    "recommendation": {"type": "string"},
                },
                "required": ["topic", "finding", "recommendation"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["patterns"],
    "additionalProperties": False,
}

_client: AnthropicLLMClient | None = None


def _get_client() -> AnthropicLLMClient:
    global _client
    if _client is None:
        if not cfg.anthropic_api_key:
            raise ValueError(
                "Clinical pattern extraction requires an Anthropic API key (ANTHROPIC_API_KEY)."
            )
        _client = AnthropicLLMClient(Role.READER, _ANTHROPIC_MODELS[Role.READER])
    return _client


def extract_and_save_patterns(document_text: str) -> int:
    """Extracts de-identified patterns from a just-finalized document and
    adds them to the pooled library. Best-effort by design — the caller
    (app/main.py's me_save_document) wraps this in a try/except, since a
    failure here must never block saving the document itself. Returns
    the number of patterns saved, for logging."""
    if not document_text.strip():
        return 0
    parsed, _usage = _get_client().chat_json(EXTRACTION_SYSTEM, document_text, _PATTERN_SCHEMA)
    patterns = parsed.get("patterns") or []
    if not patterns:
        return 0
    texts = [f"{p['finding']} → {p['recommendation']}" for p in patterns]
    embeddings = get_llm_client(Role.EMBEDDER).embed(texts)
    core_store.save_clinical_patterns([
        {**p, "embedding": e} for p, e in zip(patterns, embeddings)
    ])
    return len(patterns)


def relevant_patterns_text(query_text: str, top_k: int = 5) -> str:
    """A compact text block of the most relevant patterns from the pooled
    library for the given consult question/instruction, formatted for
    direct inclusion in a reasoning prompt — or "" if the library has
    nothing relevant yet (a brand-new platform, or an embed failure),
    which callers should treat as a no-op, not an error."""
    try:
        [query_embedding] = get_llm_client(Role.EMBEDDER).embed([query_text])
    except Exception:
        return ""
    hits = core_store.search_clinical_patterns(query_embedding, top_k=top_k)
    if not hits:
        return ""
    lines = [
        f"- [{h['topic']}] {h['finding']} → {h['recommendation']}"
        for h in hits
    ]
    return (
        "Patterns observed across other (unrelated, de-identified) "
        "consultations on this platform — general context only, never a "
        "substitute for this client's own findings:\n" + "\n".join(lines)
    )
