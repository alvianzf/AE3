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
                    "supporting_evidence_index": {
                        "type": "integer",
                        "description": "The single [E#] index of the ONE evidence passage that, alone, "
                                       "states this sentence's claim — verbatim number, no brackets. "
                                       "-1 if no single passage does.",
                    },
                },
                "required": ["sentence_index", "supporting_evidence_index"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["judgments"],
    "additionalProperties": False,
}

CHECK_SYSTEM = (
    "You are a strict fact-checker for a clinical answer. You are given "
    "numbered evidence passages and numbered answer sentences.\n\n"
    "For each sentence, check it against each evidence passage ONE AT A "
    "TIME, independently — never combine partial support from several "
    "passages into one judgment. A sentence is supported only if a SINGLE "
    "individual passage, alone, directly states its claim. Report that "
    "one passage's index. If passage A states half the claim and passage "
    "B states the other half, but neither states the whole claim on its "
    "own, the sentence is NOT supported — report -1.\n\n"
    "This matters because a pile of topically-related passages can make a "
    "claim look supported at a glance even when no single one of them "
    "actually backs it — you are checking for that specific failure, not "
    "just general relevance. Not by general medical knowledge, not by "
    "plausibility, not by a reasonable inference the evidence doesn't "
    "itself state — only by what one individual passage actually says.\n\n"
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


def _sentences(text: str) -> list[str]:
    # Markdown section headers ("## Answer") aren't checkable claims —
    # found live in specs/v6.3/02's MiniCheck prototype (the same bug
    # exists in the HHEM path's _sentences(), unfixed there since it
    # doesn't change that document's conclusion; fixed here since this
    # is a fresh implementation).
    body = " ".join(line for line in text.splitlines() if not line.strip().startswith("#"))
    return [s.strip() for s in _SENTENCE_SPLIT.split(body) if s.strip()]


# Same 700-char headroom the HHEM path uses (app/reasoning/checker.py) —
# keeps the prompt bounded regardless of how large a cited chunk is,
# though the constraint here is prompt/token budget, not a hard sequence
# limit the way HHEM's 512 tokens was.
_MAX_EVIDENCE_CHARS = 700


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

    evidence_texts = [_node_text(n) for n in reasoned.citations] + [patient_context_text[:_MAX_EVIDENCE_CHARS]]
    evidence_block = "\n".join(f"[E{i}] {t}" for i, t in enumerate(evidence_texts))
    sentence_block = "\n".join(f"[{i}] {s}" for i, s in enumerate(sentences))
    prompt = f"Evidence:\n{evidence_block}\n\nAnswer sentences to check:\n{sentence_block}"

    result, usage = get_client(Role.CHECKER).chat_json(
        CHECK_SYSTEM, prompt, CHECK_SCHEMA, max_tokens=20_000, extra_body=NO_THINKING)
    # supported = a real single evidence index was given, not just "true" —
    # mirrors the HHEM path's own per-(evidence, sentence)-pair scoring
    # (app/reasoning/checker.py): a claim only passes if one individual
    # passage backs it alone, never a same-side synthesis across several
    # passages that are each merely topic-adjacent.
    by_index = {
        j["sentence_index"]: 0 <= j.get("supporting_evidence_index", -1) < len(evidence_texts)
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
