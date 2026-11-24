"""Vision-based OCR for scanned PDF pages and photographed/screenshotted
documents — always routes to Anthropic directly, the same override
pattern Role.EMBEDDER's EMBEDDER_FORCE_LOCAL uses regardless of the live
provider toggle (app/clients/llm_client.py's get_client()): Nebius's
catalog has no model this app trusts for real multimodal reading, so OCR
doesn't follow the superadmin's chat-model provider choice at all.
"""
from __future__ import annotations

import base64

from ..clients.anthropic_client import AnthropicLLMClient
from ..clients.llm_client import Role, _ANTHROPIC_MODELS
from ..config import get_config

cfg = get_config()

OCR_SYSTEM = (
    "You transcribe scanned or photographed documents for a clinical "
    "knowledge library. Read the image carefully and output every piece "
    "of readable text exactly as written — preserve line breaks, "
    "headings, and table structure where visible. Output only the "
    "transcribed text, nothing else: no preamble, no commentary, no "
    "markdown formatting. If the image genuinely has no readable text, "
    "output exactly: [no readable text]"
)

_client: AnthropicLLMClient | None = None


def _get_client() -> AnthropicLLMClient:
    global _client
    if _client is None:
        if not cfg.anthropic_api_key:
            raise ValueError(
                "OCR requires an Anthropic API key (ANTHROPIC_API_KEY) — "
                "scanned/image ingestion has no other vision-capable path."
            )
        _client = AnthropicLLMClient(Role.READER, _ANTHROPIC_MODELS[Role.READER])
    return _client


def ocr_image(raw: bytes, media_type: str) -> str:
    """Transcribes one image's readable text via Claude vision. Returns
    "" for a page the model reports as having no readable text — never
    raises for that case, since a scanned document with a blank or purely
    decorative page is normal, not an error."""
    b64 = base64.b64encode(raw).decode("ascii")
    text, _usage = _get_client().chat_vision(OCR_SYSTEM, media_type, b64)
    text = text.strip()
    return "" if text == "[no readable text]" else text


def ocr_scanned_pdf(raw: bytes) -> list[tuple[int, str]]:
    """A scanned (image-only) PDF has no text layer for pypdf to read —
    rasterize each page and OCR it via vision instead, one Claude call
    per page so a citation can still name the page it came from, same as
    the text-layer path already does."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=raw, filetype="pdf")
    try:
        return [
            (i + 1, ocr_image(page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0)).tobytes("png"), "image/png"))
            for i, page in enumerate(doc)
        ]
    finally:
        doc.close()
