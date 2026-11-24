"""LLM-as-judge anti-hallucination check — an alternative to the local
HHEM classifier (app/reasoning/checker.py). Added specs/v6.3/02: HHEM
costs 28-77s/call on this VPS's CPU, and a smaller local classifier
(MiniCheck-RoBERTa-Large) was tried and came back *worse* (185s/call),
pointing at CPU-only inference itself as the bottleneck, not model
choice. This offloads scoring to Nebius's own infrastructure instead —
one batched Role.CHECKER `chat_json` call judging every answer sentence
against its citations at once, mirroring app/retrieval/traversal.py's
`llm_judge_relevance()` pattern (one batched judgment call per hop,
same idea applied here to one batched judgment call per check()).

This is the "last measure" fallback specs/v6.3/01 flagged, not a
claimed improvement in rigor: an LLM judging another LLM's output is a
philosophically weaker guarantee than a classifier trained specifically
to catch unsupported claims. Traded deliberately for latency that
doesn't require this VPS's own CPU or memory budget.
"""
from __future__ import annotations

import re

from ..clients.llm_client import NO_THINKING, Role, get_client
from ..graph import store
from .reasoner import ReasonedAnswer

CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "judgments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sentence_index": {"type": "integer", "description": "The sentence's [N] index, verbatim."},
                    "supporting_evidence_indices": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Every [E#] evidence index (verbatim numbers, no brackets) whose "
                                       "stated facts, combined, ground this sentence — one index if a "
                                       "single passage states the whole claim, several if it takes more "
                                       "than one passage's facts together to ground it. Empty if nothing "
                                       "in the evidence grounds it, even combined.",
                    },
                },
                "required": ["sentence_index", "supporting_evidence_indices"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["judgments"],
    "additionalProperties": False,
}

CHECK_SYSTEM = (
    "You are a fact-checker for a clinical answer. You are given numbered "
    "evidence passages and numbered answer sentences.\n\n"
    "For each sentence, decide whether it is actually grounded in the "
    "evidence — not whether it is phrased exactly as the evidence phrases "
    "it. A sentence is grounded if:\n"
    "- a single passage states its claim directly, or\n"
    "- combining the facts stated across two or more passages establishes "
    "it (e.g. one passage gives a value, another states what that value "
    "indicates — together they ground a sentence connecting the two), or\n"
    "- it is a reasonable clinical inference drawn directly from facts the "
    "evidence actually states — ordinary clinical reasoning connecting "
    "those stated facts to a conclusion, not a new fact standing on its "
    "own. Report the evidence index(es) the inference is actually drawn "
    "from.\n\n"
    "A sentence is NOT grounded — report an empty list — if:\n"
    "- it states a specific fact, value, or finding that no passage gives, "
    "combined or otherwise (this is the failure this check exists to "
    "catch: a pile of topically-related passages can make an invented "
    "detail look supported at a glance), or\n"
    "- it borrows a premise from outside medical knowledge that the "
    "evidence itself never supplies — interpreting a stated fact is fine, "
    "inventing one isn't, or\n"
    "- it states something as established or certain that the evidence "
    "only supports as a possibility.\n\n"
    "Judge every sentence independently and return exactly one judgment "
    "per sentence index given."
)


def is_loaded() -> bool:
    """No local model to lazily load — always 'ready' in the sense the
    HHEM Checker's is_loaded() means it (app/reasoning/checker.py)."""
    return True


def ping() -> dict:
    return {"loaded": True, "note": "LLM-as-judge — no local model, judged via Role.CHECKER"}


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_BULLET_PREFIX = re.compile(r"^(?:[-*•]|\d+[.)])\s+")
_BOLD_ONLY_LINE = re.compile(r"^\*\*[^*]+\*\*:?$")


def _sentences(text: str) -> list[str]:
    # Found live: joining every line with a single space before splitting
    # on sentence punctuation (the previous approach) turned a bulleted
    # list — each item a separate, independently-cited claim, often with
    # no terminal period — into one run-on blob, so two adjacent bullets
    # (each individually well-grounded in its own single citation) merged
    # into one "sentence" that no single passage could possibly ground as
    # a whole. That merged, garbled unit is what the checker was actually
    # flagging as unsupported, not the real claims the reasoner wrote —
    # this was the dominant cause of a real answer coming back gutted.
    # Splitting on newlines FIRST, before punctuation, keeps each
    # markdown line (paragraph, bullet, list item) — almost always one
    # coherent claim in these answers — as its own unit; multi-sentence
    # lines still get split further by punctuation within that line.
    sentences: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = _BULLET_PREFIX.sub("", line)
        if not line or _BOLD_ONLY_LINE.match(line):
            # A bare "**Lab markers**" subsection title carries no claim
            # to verify — including it would always get (correctly, but
            # uselessly) flagged as unsupported, since it cites nothing
            # and states no fact.
            continue
        sentences.extend(s.strip() for s in _SENTENCE_SPLIT.split(line) if s.strip())
    return sentences


# Found live, testing a real consultation: every single retrieved chunk
# (10/10 in that run, 700-2200 chars each — chunk_size is configured at
# 1200 but a chunk can run longer) exceeded the old 700-char figure
# inherited from the HHEM path (app/reasoning/checker.py), which needed
# it as a hard embedding-sequence limit — this path has no such limit,
# only a prompt/token budget, and 700 chars routinely cut a chunk off
# before the specific detail a citation actually drew from. The reasoner
# itself sees the full, untruncated chunk when writing the answer, so a
# claim grounded in the back half of a long passage was being judged
# against only the front half — exactly the kind of well-cited claim
# that was wrongly coming back "unsupported." 3000 chars comfortably
# covers essentially every real chunk seen so far; 10 citations at that
# size is still a modest prompt for a single chat_json call.
_MAX_EVIDENCE_CHARS = 3000

# patient_context_text is one block covering the whole patient (labs,
# conditions, and now any uploaded documents — app/patient/context.py),
# not a single retrieved chunk — the 700-char citation-chunk budget above
# cut it off before ever reaching an uploaded document's content (found
# live: a real 20K-char lab panel the reasoner correctly used got checked
# against only the first 700 chars of patient context, which never even
# reached the "Uploaded documents" section appended at the end of
# as_query_text() — every lab-grounded sentence was marked unsupported
# and stripped from the final answer). Large enough to actually cover a
# real uploaded lab panel, not just the context block's opening lines.
_MAX_PATIENT_CONTEXT_CHARS = 20_000


def _node_text(node: dict) -> str:
    if store.is_chunk(node):
        text = node["text"]
    else:
        text = f"{node.get('name', '')} ({store.node_type(node)})"
    return text[:_MAX_EVIDENCE_CHARS]


_ZERO_USAGE = {"input_tokens": 0, "output_tokens": 0}


def check(question: str, reasoned: ReasonedAnswer, patient_context_text: str) -> dict:
    """Same contract as app/reasoning/checker.py's check(), plus a
    `usage` key (real token spend — this call costs real tokens, unlike
    the local HHEM path) that callers can track the same way every other
    role's usage is tracked.

    One batched call for the whole answer, not one call per (evidence,
    sentence) pair — keeps this to a single ~2-5s round-trip regardless
    of how many sentences or citations a real answer has, the same
    reasoning traversal.py's per-hop relevance judge already relies on.
    """
    sentences = _sentences(reasoned.text)
    if not sentences:
        return {"verdict": "pass", "unsupported": [], "note": "Nothing to check.", "usage": dict(_ZERO_USAGE)}

    evidence_texts = [_node_text(n) for n in reasoned.citations] + [patient_context_text[:_MAX_PATIENT_CONTEXT_CHARS]]
    evidence_block = "\n".join(f"[E{i}] {t}" for i, t in enumerate(evidence_texts))
    sentence_block = "\n".join(f"[{i}] {s}" for i, s in enumerate(sentences))
    prompt = f"Evidence:\n{evidence_block}\n\nAnswer sentences to check:\n{sentence_block}"

    result, usage = get_client(Role.CHECKER).chat_json(
        CHECK_SYSTEM, prompt, CHECK_SCHEMA, max_tokens=20_000, extra_body=NO_THINKING)
    # supported = at least one real evidence index was given — a claim can
    # be grounded by combining facts across several passages (or a
    # reasonable inference drawn from them), not only by one single
    # passage stating it verbatim; see CHECK_SYSTEM. Still fails closed:
    # an index out of range, or an empty list, means not grounded.
    by_index = {
        j["sentence_index"]: any(
            0 <= idx < len(evidence_texts) for idx in j.get("supporting_evidence_indices", [])
        )
        for j in result["judgments"]
    }
    # A sentence the model drops from its response is treated as
    # unsupported, not silently passed — fail-closed, same rule the HHEM
    # path's max()-below-threshold check enforces implicitly.
    unsupported = [s for i, s in enumerate(sentences) if not by_index.get(i, False)]

    verdict = "weak" if unsupported else "pass"
    note = (
        f"{len(unsupported)} sentence(s) not confidently supported by any single cited "
        "source." if unsupported else
        "Every sentence checked against its cited sources."
    )
    return {"verdict": verdict, "unsupported": unsupported, "note": note, "usage": usage}
