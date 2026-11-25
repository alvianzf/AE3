"""Mandatory citation-grounding gate for agentic retrieval
(app/retrieval/agentic.py) — the one failure mode specific to that
architecture with no analogue in the fixed pipeline ("deceptive
grounding": a cited chunk is real, but doesn't actually support the
specific claim attributed to it — this session's architecture-decision
research flagged this as the sharpest risk of the agentic design and
required this gate be non-negotiable, not optional polish). Run on every
agentic answer before it's logged as usable (scripts/shadow_eval_agentic.py).

Simpler than app/reasoning/llm_checker.py's full-answer check: grounding
here is structural, not inferred from regex-parsed [N] markers — the
agent's own submit_answer citations already declare exactly which chunk
backs which claim (app/retrieval/agentic.py's _SUBMIT_ANSWER_SCHEMA), so
the evidence set for this check is exactly the cited chunks, nothing
else — cheap by construction.
"""
from __future__ import annotations

from ..clients.llm_client import NO_THINKING, Role, get_client

_ZERO_USAGE = {"input_tokens": 0, "output_tokens": 0}

CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "judgments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "The citation's position, verbatim."},
                    "grounded": {
                        "type": "boolean",
                        "description": "True only if the cited passage actually states or "
                                       "directly supports the specific claim in `supports` — "
                                       "not merely the same general topic.",
                    },
                },
                "required": ["index", "grounded"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["judgments"],
    "additionalProperties": False,
}

CHECK_SYSTEM = (
    "You check whether each claimed citation actually supports the specific "
    "claim it's attached to — not whether the passage is on the same general "
    "topic. A citation is grounded only if the passage directly states or "
    "clearly entails the specific claim. A passage about the same condition, "
    "drug, or marker that doesn't actually say the specific thing claimed is "
    "NOT grounded — this is specifically the failure this check exists to "
    "catch: a real, relevant-looking citation attached to a claim it doesn't "
    "actually back.\n\n"
    "Judge every citation independently and return exactly one judgment per "
    "citation index given."
)


def check_grounding(citations: list[dict], chunk_texts: dict[str, str]) -> dict:
    """`citations` is [{"chunk_id", "supports"}, ...] from the agent's own
    submit_answer call. `chunk_texts` maps chunk_id -> its full text,
    built from the tool-call trace (app/retrieval/agentic.py's run()) —
    exactly what the agent actually saw, not re-fetched separately.

    A citation whose chunk_id isn't in chunk_texts at all (the model
    invented an id, or cited something it never actually retrieved) fails
    closed as ungrounded without spending a judgment call on it — there's
    nothing to check it against."""
    if not citations:
        return {"verdict": "pass", "flagged": [], "usage": dict(_ZERO_USAGE)}

    checkable = [c for c in citations if c.get("chunk_id") in chunk_texts]
    missing = [c for c in citations if c.get("chunk_id") not in chunk_texts]

    if not checkable:
        return {"verdict": "flagged", "flagged": missing, "usage": dict(_ZERO_USAGE)}

    evidence_block = "\n".join(
        f"[{i}] (from {c['chunk_id']}): {chunk_texts[c['chunk_id']]}\nClaimed to support: {c['supports']}"
        for i, c in enumerate(checkable)
    )
    prompt = f"Citations to check:\n{evidence_block}"
    result, usage = get_client(Role.CHECKER).chat_json(
        CHECK_SYSTEM, prompt, CHECK_SCHEMA, max_tokens=20_000, extra_body=NO_THINKING)
    by_index = {j["index"]: j.get("grounded", False) for j in result["judgments"]}
    flagged = [c for i, c in enumerate(checkable) if not by_index.get(i, False)] + missing

    verdict = "flagged" if flagged else "pass"
    return {"verdict": verdict, "flagged": flagged, "usage": usage}
