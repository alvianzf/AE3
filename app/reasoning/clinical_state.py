"""Lab-marker extraction for the living client clinical state
(specs/v9/03) — turns a free-text lab entry (record_entries.content for
kind='lab', e.g. "Ferritin 8.10 µg/L (ref 10.0–291.0)", sometimes a
whole pasted panel in one entry) into structured marker rows
(app/vault.py's upsert_clinical_state_marker).

Runs in the background, after the raw entry is already saved
(app/main.py's BackgroundTasks) — never inline in a practitioner's "add
entry" action, and never in the live consult path. Best-effort by
design: a failed extraction must not be a failed save, since the raw
record_entries row is already the real, authoritative data regardless
of whether this derived view updates.
"""
from __future__ import annotations

import logging

from .. import vault
from ..clients.llm_client import NO_THINKING, Role, get_client

_log = logging.getLogger(__name__)

EXTRACT_MARKERS_SCHEMA = {
    "type": "object",
    "properties": {
        "markers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "The marker's name, as "
                              "written (e.g. 'Ferritin', 'Fasting insulin')."},
                    "value": {"type": "string", "description": "The numeric result, as a "
                              "plain number string (e.g. '8.10'), no unit attached."},
                    "unit": {"type": "string", "description": "The unit, if given (e.g. "
                             "'µg/L'). Empty string if none."},
                    "reference_range": {"type": "string", "description": "The reference "
                                        "range as printed, if given (e.g. '10.0-291.0'). "
                                        "Empty string if none."},
                    "flag": {"type": "string", "enum": ["high", "low", "in_range", "unknown"],
                             "description": "'unknown' if no reference range was given to "
                                            "judge against — never guess a normal range."},
                },
                "required": ["label", "value", "unit", "reference_range", "flag"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["markers"],
    "additionalProperties": False,
}

EXTRACT_MARKERS_SYSTEM = (
    "You extract every distinct lab marker reported in a piece of clinical "
    "text — this may be a single value, or a whole panel with many markers "
    "in one block of text. For each marker, extract exactly what's stated: "
    "the name, the numeric value, the unit, and the reference range if one "
    "is given.\n\n"
    "Judge `flag` only from a reference range actually present in the "
    "text — if none is given, flag is 'unknown', never a guessed normal "
    "range from general medical knowledge. If the text states a result "
    "is already flagged (e.g. 'low', 'high', an asterisk, a note like "
    "'(L)'), that stated flag wins over your own range comparison.\n\n"
    "Extract only real markers with an actual value — skip narrative text, "
    "dates, client identifiers, and anything with no numeric result. If "
    "nothing extractable is present, return an empty list."
)


def extract_lab_markers(content: str) -> tuple[list[dict], dict]:
    result, usage = get_client(Role.CHECKER).chat_json(
        EXTRACT_MARKERS_SYSTEM, content, EXTRACT_MARKERS_SCHEMA, extra_body=NO_THINKING)
    return result.get("markers") or [], usage


def update_lab_state(practitioner_id: str, client_id: str, entry: dict) -> None:
    """Entry point for app/main.py's BackgroundTasks. Never raises — a
    logged failure here leaves client_clinical_state exactly as it was,
    which is a stale-but-honest state, not a corrupted one; the raw
    entry this was extracted from is unaffected either way."""
    try:
        markers, _usage = extract_lab_markers(entry["content"])
    except Exception:
        _log.exception("lab-marker extraction failed for entry %s (client %s)",
                       entry.get("id"), client_id)
        return
    for m in markers:
        try:
            vault.upsert_clinical_state_marker(
                practitioner_id, client_id, label=m["label"], value=m.get("value") or None,
                unit=m.get("unit") or None, reference_range=m.get("reference_range") or None,
                flag=m.get("flag"), source_entry_id=entry["id"],
            )
        except Exception:
            _log.exception("clinical-state upsert failed for marker %r (entry %s)",
                           m.get("label"), entry.get("id"))
