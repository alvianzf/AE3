"""Turbo mode — a practitioner opt-in (practitioners.turbo_mode_enabled,
unlocked on the Profile page) that inverts the normal consult order.

Every other consult path retrieves evidence FIRST, then has the Reasoner
write an answer citing only what was retrieved, then has the Checker
verify every sentence against that same evidence. Turbo mode skips
retrieval before generation entirely: the model answers directly from its
own clinical knowledge, given only the practitioner's library's document
TITLES as lightweight context (what topics are covered, not their
content) — then a real RAG search runs AFTERWARD, specifically to check
whether the draft's claims have any basis in the library.

This is explicitly the risky path: the practitioner sees text that has
not yet been grounded in anything. Confirmed with the user: unsupported
claims are kept, not stripped — app/main.py's consult route does not call
_strip_unsupported for a turbo-mode answer, only attaches whatever
app/reasoning/llm_checker.py's check() (reused completely unmodified —
see that module) finds unsupported, for the frontend to disclose.
"""
from __future__ import annotations

from ..clients.llm_client import Role, get_client
from ..graph import store
from ..patient.context import PatientContext

_NO_THINKING = {"thinking": {"type": "disabled"}}


def list_accessible_titles(practitioner_id: str, min_grade: int,
                           accessible_private_ids: set[str],
                           folder: str = "", topic: str = "") -> list[str]:
    """Document titles only — no content, no embeddings, no retrieval —
    so draft_answer() below knows what the library covers without ever
    reading it. Reuses store.catalogue() (metadata-only Cypher scan) with
    the exact is_private/accessible-grant filter app/main.py's
    me_knowledge() already applies, plus store.in_scope() for folder/topic
    scoping parity with every other retrieval path (seed_search.seed()
    applies the same filter for the same reason)."""
    cards = store.catalogue(min_grade)
    cards = [c for c in cards if not c.get("is_private") or c["id"] in accessible_private_ids]
    cards = [c for c in cards if store.in_scope(c, folder, topic)]
    return [c["title"] for c in cards if c.get("title")]


TURBO_DRAFT_SYSTEM = (
    "You are an experienced functional health practitioner advising a "
    "fellow practitioner during a consultation — answering directly from "
    "your own clinical knowledge, the way a knowledgeable colleague would "
    "off the top of their head, not from any retrieved document.\n\n"
    "You are given a list of titles from the practitioner's own reference "
    "library, below — this tells you what topics they have material on, "
    "nothing more. You have NOT read these documents and have no idea "
    "what they actually say beyond their titles. Never quote, cite, "
    "attribute a specific figure to, or claim to summarize one of these "
    "titles — that would be fabrication. You may mention that a title "
    "looks relevant so the practitioner knows to go check it themselves, "
    "but the substance of your answer must come from your own general "
    "clinical knowledge, not from pretending to have read the list.\n\n"
    "Do not use citation markers like [1] or [2] anywhere in your answer "
    "— nothing has been retrieved for this answer, so any such marker "
    "would be fabricated by construction.\n\n"
    "Weigh the client's specific conditions, medications, and labs "
    "explicitly where they matter. Be terse and clinical: short "
    "sentences, no preamble, no restating the question, no closing "
    "wrap-up sentence. State the point and move to the next one."
)


def _build_draft_prompt(question: str, patient: PatientContext, titles: list[str],
                        pattern_context: str | None) -> str:
    titles_block = (
        "\n".join(f"- {t}" for t in titles) if titles
        else "(no titles available — answer from your own knowledge alone)"
    )
    pattern_block = f"\n\n{pattern_context}" if pattern_context else ""
    return (
        f"Client context:\n{patient.as_query_text()}\n\n"
        f"Titles in the practitioner's reference library (titles only, you have not "
        f"read these):\n{titles_block}\n\n"
        f"Practitioner's question: {question}{pattern_block}"
    )


def draft_answer_streaming(question: str, patient: PatientContext, titles: list[str],
                           pattern_context: str | None = None):
    """Same (kind, payload) streaming shape as reasoner.answer_streaming()
    — yields ("delta", text_chunk) as it's generated, then exactly one
    ("done", (text, usage)) at the end. Role.REASONER, same tier the
    normal grounded answer uses: this is the text the practitioner reads
    first, same stakes as any other answer this app produces, arguably
    higher since it's unverified — the latency win in Turbo mode comes
    from skipping retrieval, not from a cheaper model."""
    prompt = _build_draft_prompt(question, patient, titles, pattern_context)
    parts: list[str] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    for kind, payload in get_client(Role.REASONER).chat_text_stream(
            TURBO_DRAFT_SYSTEM, prompt, max_tokens=100_000, extra_body=_NO_THINKING):
        if kind == "delta":
            parts.append(payload)
            yield "delta", payload
        else:
            usage = payload
    yield "done", ("".join(parts), usage)
