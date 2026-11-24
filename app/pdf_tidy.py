"""Tidies a finalized document's saved HTML into clean, consistently
formatted markup before it's wrapped into a PDF — always via Claude
directly, the same override pattern app/ingestion/ocr.py uses regardless
of the live provider toggle (app/clients/llm_client.py's get_client()):
this is a formatting pass over an already-written document, not a live
consult/chat round-trip the superadmin's provider choice is meant to
govern.

The result is cached by app/main.py's PDF route (vault.save_pdf_cache),
keyed by a hash of the document's own `content` — a document that hasn't
changed since its last PDF reuses that cached HTML instead of spending
another Claude call on every download or preview.
"""
from __future__ import annotations

from .clients.anthropic_client import AnthropicLLMClient
from .clients.llm_client import Role, _ANTHROPIC_MODELS
from .config import get_config

cfg = get_config()

TIDY_SYSTEM = (
    "You clean up the HTML of a clinical document (a clinician note or a "
    "client report) so it prints as a polished, professional PDF. You will "
    "be given an HTML fragment: headings, paragraphs, lists, tables, "
    "images, and numbered citation markers (<sup class=\"cite\"> elements) "
    "with a References list at the end.\n\n"
    "Your ONLY job is to tidy structure and formatting: fix inconsistent "
    "spacing, redundant or empty tags, awkward or broken nesting, and "
    "inconsistent heading levels; make tables well-formed; keep paragraph "
    "and list structure clean and readable. Every <img> tag in the input "
    "is a real image already placed in this document by the practitioner "
    "— keep every one of them in the output, in place, with its src and "
    "other attributes unchanged; never drop, replace, or move an image "
    "out of its original context.\n\n"
    "You must NEVER change the actual content: do not add, remove, "
    "reword, summarize, or correct a single fact, number, name, finding, "
    "or recommendation. Preserve every <sup class=\"cite\"> citation "
    "marker and its data-locator/data-doc-id attributes exactly, the "
    "References list exactly, and every <img> tag exactly — these are "
    "functional, not decorative.\n\n"
    "Output ONLY the cleaned HTML fragment. No markdown code fences, no "
    "preamble, no explanation — just the HTML."
)

_client: AnthropicLLMClient | None = None


def _get_client() -> AnthropicLLMClient:
    global _client
    if _client is None:
        if not cfg.anthropic_api_key:
            raise ValueError(
                "PDF tidying requires an Anthropic API key (ANTHROPIC_API_KEY)."
            )
        _client = AnthropicLLMClient(Role.READER, _ANTHROPIC_MODELS[Role.READER])
    return _client


def tidy_document_html(content: str) -> str:
    """Returns a cleaned-up version of `content` for PDF export. Raises on
    failure, or on an implausibly short result (a truncated or otherwise
    broken generation) — the caller (app/main.py's me_download_document_pdf)
    catches this and falls back to the original content rather than ever
    blocking the PDF on a formatting pass."""
    text, _usage = _get_client().chat_text(TIDY_SYSTEM, content, max_tokens=16_000)
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    text = text.strip()
    if len(text) < len(content) * 0.5:
        raise ValueError("tidied HTML looks truncated or empty relative to the source content")
    return text
