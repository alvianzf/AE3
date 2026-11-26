"""AI document understanding for the unified client Record (specs/v9) —
reads any file a practitioner or client uploads, figures out what kind of
document it is, writes a short summary, and surfaces a handful of
highlights (anything a practitioner should notice at a glance: an
abnormal value, a new diagnosis, a medication note).

Runs in the background, after the file and its record_entries row are
already saved (app/main.py's BackgroundTasks) — never inline in the
upload request. Best-effort by design, same contract as
app/reasoning/clinical_state.py's update_lab_state: a failed
classification must not be a failed upload, and just leaves
uploaded_files.ai_doc_type NULL (shown in the UI as "processing" or
"unavailable", never as a broken upload).

Deliberately its own taxonomy/schema, not a reuse of
app/ingestion/pipeline.py's Reader (READER_SCHEMA/doc_type) — that one
classifies shared-library documents into folder/topic terms meant for
retrieval scoping; a client's own uploaded file needs a clinical-record
taxonomy instead (lab result, imaging report, prescription, etc.), not
a library folder suggestion.
"""
from __future__ import annotations

import logging

from .. import vault
from ..clients.llm_client import NO_THINKING, Role, get_client
from ..ingestion.pipeline import _reader_sample

_log = logging.getLogger(__name__)

DOC_TYPES = ("lab_result", "imaging_report", "clinical_note", "prescription",
             "intake_form", "insurance", "referral", "other")

CLASSIFY_DOCUMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_type": {"type": "string", "enum": list(DOC_TYPES),
                     "description": "What kind of document this is."},
        "summary": {"type": "string", "description": "1-2 sentences on what this "
                    "document is and what it covers."},
        "highlights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "A single flagged or "
                             "important point — an abnormal result, a new or changed "
                             "diagnosis, a medication or interaction note, an urgent "
                             "referral — anything a practitioner should not miss "
                             "skimming this file."},
                    "severity": {"type": "string", "enum": ["flag", "info"],
                                 "description": "'flag' for anything abnormal or "
                                                "needing attention, 'info' for routine "
                                                "but noteworthy context."},
                },
                "required": ["text", "severity"],
                "additionalProperties": False,
            },
            "description": "0-5 short highlights. Empty list if nothing in the "
                           "document is notable beyond the summary.",
        },
    },
    "required": ["doc_type", "summary", "highlights"],
    "additionalProperties": False,
}

CLASSIFY_DOCUMENT_SYSTEM = (
    "You are reviewing a document uploaded to a client's clinical record for "
    "a Functional Health Practitioner. Identify what kind of document this "
    "is, write a 1-2 sentence summary of what it covers, and list up to 5 "
    "short highlights — anything a practitioner should notice at a glance: "
    "an abnormal lab value, a new or changed diagnosis, a prescribed "
    "medication or an interaction/allergy note, an urgent referral, and so "
    "on. Mark each highlight 'flag' if it's abnormal or needs attention, "
    "'info' if it's just noteworthy context.\n\n"
    "Extract only what the text actually supports — never infer a "
    "diagnosis, risk, or interpretation that isn't stated. If there is "
    "genuinely nothing notable beyond the summary, return an empty "
    "highlights list."
)


def classify_document(practitioner_id: str, client_id: str, file_id: str,
                      extracted_text: str, filename: str) -> None:
    """Entry point for app/main.py's BackgroundTasks. Never raises — a
    logged failure here leaves uploaded_files.ai_doc_type/ai_summary NULL,
    a stale-but-honest "not yet classified" state, never a broken upload."""
    try:
        prompt = f"Filename: {filename}\n\nDocument text:\n---\n{_reader_sample(extracted_text)}\n---"
        card, _usage = get_client(Role.CHECKER).chat_json(
            CLASSIFY_DOCUMENT_SYSTEM, prompt, CLASSIFY_DOCUMENT_SCHEMA,
            max_tokens=1_000, extra_body=NO_THINKING)
    except Exception:
        _log.exception("document classification failed for file %s (client %s)",
                       file_id, client_id)
        return
    try:
        vault.save_document_insights(
            practitioner_id, file_id, doc_type=card["doc_type"],
            summary=card["summary"], highlights=card.get("highlights") or [],
        )
    except Exception:
        _log.exception("saving document insights failed for file %s (client %s)",
                       file_id, client_id)
