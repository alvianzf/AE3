"""get_patient_context(): the patient data that shapes retrieval, not just
gets appended at the end (see retrieval/seed_search.py and
retrieval/traversal.py for where this actually gets used).

**Real assumption, worth flagging rather than hiding**: the brief for this
asked for a MySQL patient lookup with clean conditions/medications/labs
columns. This repo has no MySQL — patient ("client") data lives in a
per-practitioner SQLite vault (app/vault.py), where clinical detail is
free-text `record_entries` tagged by kind (lab/history/note/condition/
medication — the last two added alongside this module, see vault.py's
KINDS) plus a JSON questionnaire-response blob. This function adapts to
that, on the explicit decision to not stand up a new database for this.

Two real data-quality gaps this surfaces rather than hides:
1. Entries recorded before "condition"/"medication" existed as kinds are
   filed under "history"/"note" — get_patient_context() cannot tell a
   past condition from a current medication in that older data. It
   returns them separately as `legacy_notes` rather than guessing which
   bucket they belong in.
2. The questionnaire response is a free-form JSON blob (question -> answer
   text), not structured clinical fields — it's included as supplementary
   text, not parsed into conditions/medications.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .. import vault


@dataclass
class PatientContext:
    client_id: str
    name: str
    dob: str | None
    country: str | None
    conditions: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    recent_labs: list[dict] = field(default_factory=list)
    legacy_notes: list[dict] = field(default_factory=list)
    questionnaire_summary: str = ""

    def as_query_text(self) -> str:
        """A compact text block for conditioning an LLM call (seed search
        query formation, per-hop relevance judgment, final reasoning) —
        every one of those call sites should use this, not just the raw
        question, per the clinical-safety requirement this module exists
        for."""
        lines = [f"Patient: {self.name}"]
        if self.dob:
            lines.append(f"DOB: {self.dob}")
        lines.append(f"Active conditions: {', '.join(self.conditions) or 'none recorded'}")
        lines.append(f"Current medications: {', '.join(self.medications) or 'none recorded'}")
        if self.recent_labs:
            labs = "; ".join(f"{l['content']} ({l['date']})" for l in self.recent_labs)
            lines.append(f"Recent labs: {labs}")
        if self.legacy_notes:
            legacy = "; ".join(f"[{n['kind']}] {n['content']}" for n in self.legacy_notes)
            lines.append(f"Other recorded history/notes: {legacy}")
        if self.questionnaire_summary:
            lines.append(f"Questionnaire responses: {self.questionnaire_summary}")
        return "\n".join(lines)


# How many most-recent lab entries count as "recent" — a config value would
# be over-engineering for a single call site; hardcoded and named clearly
# per CLAUDE.md's "hardcode until there's a real reason to configure it".
_RECENT_LAB_COUNT = 10


def get_patient_context(practitioner_id: str, client_id: str) -> PatientContext | None:
    client = vault.get_client(practitioner_id, client_id)
    if client is None:
        return None

    conditions, medications, labs, legacy = [], [], [], []
    for entry in client["entries"]:
        kind, content = entry["kind"], entry["content"]
        if kind == "condition":
            conditions.append(content)
        elif kind == "medication":
            medications.append(content)
        elif kind == "lab":
            labs.append({"content": content, "date": entry["created_at"][:10]})
        elif kind in ("history", "note"):
            legacy.append({"kind": kind, "content": content})
        # "session_summary" entries are consult history, not patient
        # baseline data — deliberately excluded from retrieval-shaping
        # context; a past AI answer shouldn't bias what the next
        # traversal considers relevant.

    response = vault.get_questionnaire_response(practitioner_id, client_id)
    questionnaire_summary = ""
    if response:
        answers = response.get("answers") or {}
        questionnaire_summary = "; ".join(f"{q}: {a}" for q, a in answers.items())

    return PatientContext(
        client_id=client_id,
        name=client["name"],
        dob=client.get("dob"),
        country=client.get("country"),
        conditions=conditions,
        medications=medications,
        recent_labs=labs[-_RECENT_LAB_COUNT:],
        legacy_notes=legacy,
        questionnaire_summary=questionnaire_summary,
    )
