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
    protocols: list[str] = field(default_factory=list)
    recent_labs: list[dict] = field(default_factory=list)
    legacy_notes: list[dict] = field(default_factory=list)
    questionnaire_summary: str = ""
    # Filenames only — always present regardless of the current question,
    # so the model (and the "none on file" vs "N on file" distinction)
    # doesn't depend on whether this question's vector search happened to
    # surface anything. The actual content lives in uploaded_documents
    # below, populated separately by load_relevant_documents() once a
    # question is known — see that function's docstring for why this
    # isn't just eagerly loaded here.
    uploaded_document_names: list[str] = field(default_factory=list)
    uploaded_documents: list[dict] = field(default_factory=list)

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
        lines.append(f"Client-specific protocols (implemented by practitioner): {', '.join(self.protocols) or 'none active'}")
        # Always stated, never omitted when empty — same as conditions/
        # medications above. An omitted line reads as "not checked"; an
        # explicit "none recorded" gives the Reasoner real grounds to say
        # so plainly instead of writing a placeholder like "[lab results]"
        # for a gap it can't otherwise tell apart from data that just
        # wasn't looked at (found live, 2026-09-14).
        if self.recent_labs:
            labs = "; ".join(f"{l['content']} ({l['date']})" for l in self.recent_labs)
            lines.append(f"Recent labs: {labs}")
        else:
            lines.append("Recent labs: none recorded")
        if self.legacy_notes:
            legacy = "; ".join(f"[{n['kind']}] {n['content']}" for n in self.legacy_notes)
            lines.append(f"Other recorded history/notes: {legacy}")
        else:
            lines.append("Other recorded history/notes: none recorded")
        lines.append(f"Questionnaire responses: {self.questionnaire_summary or 'none recorded'}")
        if self.uploaded_document_names:
            lines.append(f"Uploaded documents on file: {', '.join(self.uploaded_document_names)}")
        else:
            lines.append("Uploaded documents on file: none")
        if self.uploaded_documents:
            lines.append("Excerpts from uploaded documents relevant to the current question:")
            for doc in self.uploaded_documents:
                lines.append(f"--- from {doc['name']} ---\n{doc['text']}")
        return "\n".join(lines)


# How many most-recent lab entries count as "recent" — a config value would
# be over-engineering for a single call site; hardcoded and named clearly
# per CLAUDE.md's "hardcode until there's a real reason to configure it".
_RECENT_LAB_COUNT = 10

# How many of the most relevant uploaded-document chunks to surface per
# question (app/vault.py's search_client_documents) — question-scoped
# retrieval, not a flat dump of every uploaded file's full text. That
# flat-dump approach was the first fix tried here and didn't scale past
# a client with a file or two (found live: a single 20K-char lab panel
# alone ate ~5K tokens of every prompt, relevant or not) — a long-term
# client with years of lab panels and prior documents needs retrieval,
# the same reasoning the library's own chunk+embed+search already rests
# on, just scoped to one client instead of the whole library.
_RELEVANT_CHUNK_COUNT = 8


def get_patient_context(practitioner_id: str, client_id: str) -> PatientContext | None:
    client = vault.get_client(practitioner_id, client_id)
    if client is None:
        return None

    conditions, medications, protocols, labs, legacy = [], [], [], [], []
    for entry in client["entries"]:
        kind, content = entry["kind"], entry["content"]
        if kind == "condition":
            conditions.append(content)
        elif kind == "medication":
            medications.append(content)
        elif kind == "protocol":
            protocols.append(content)
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

    uploaded_document_names = [
        f["original_name"] for f in vault.list_uploaded_files(practitioner_id, client_id)
        if f.get("extraction_status") == "done"
    ]

    return PatientContext(
        client_id=client_id,
        name=client["name"],
        dob=client.get("dob"),
        country=client.get("country"),
        conditions=conditions,
        medications=medications,
        protocols=protocols,
        recent_labs=labs[-_RECENT_LAB_COUNT:],
        legacy_notes=legacy,
        questionnaire_summary=questionnaire_summary,
        uploaded_document_names=uploaded_document_names,
    )


def load_relevant_documents(patient: PatientContext, practitioner_id: str, query_text: str) -> None:
    """Mutates patient.uploaded_documents in place with the chunks most
    relevant to `query_text` (the practitioner's actual consult question,
    or — for document drafting, which has no single "question" — the
    instruction/kind given there). Separate from get_patient_context()
    because it needs an embedding call (a real request, not free) and a
    query to embed against; get_patient_context() alone is cheap and
    callable without knowing yet what's being asked. A no-op (leaves
    uploaded_documents empty) if the client has no uploaded documents at
    all or the embed call itself fails — callers already render "none on
    file" correctly from uploaded_document_names in that case, so this
    degrades to the pre-retrieval behavior rather than erroring the
    whole consult."""
    if not patient.uploaded_document_names:
        return
    from ..clients.llm_client import Role, get_client
    try:
        [query_embedding] = get_client(Role.EMBEDDER).embed([query_text])
    except Exception:
        return
    hits = vault.search_client_documents(
        practitioner_id, patient.client_id, query_embedding, top_k=_RELEVANT_CHUNK_COUNT)
    patient.uploaded_documents = [{"name": h["file_name"], "text": h["text"]} for h in hits]
