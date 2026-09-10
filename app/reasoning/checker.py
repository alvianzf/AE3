"""Anti-hallucination check on the Reasoner's answer — carried forward
from specs/v4.2 into this architecture (ported out of the now-deleted
app/llm.py) since "an independent check challenges every answer" is a
marketed, load-bearing safety feature, same treatment as the grade
system in specs/v4.2/01#decided-what-consumes-the-embedders-output's
sibling decision to carry `grade` forward onto Document.

Not a chat-model call — HHEM-2.1-Open is a hallucination-detection
classifier, scored directly, no LLM role/client involved. See
app/config.py's checker_model/checker_threshold.
"""
from __future__ import annotations

import re

from ..config import get_config
from ..graph import store
from .reasoner import ReasonedAnswer

cfg = get_config()

_checker_model = None


def _get_checker_model():
    """Lazy singleton — only pay the transformers/torch import + model
    download cost the first time check() actually runs."""
    global _checker_model
    if _checker_model is None:
        from transformers import AutoModelForSequenceClassification
        _checker_model = AutoModelForSequenceClassification.from_pretrained(
            cfg.checker_model, trust_remote_code=True)
    return _checker_model


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def _node_text(node: dict) -> str:
    if store.is_chunk(node):
        return node["text"]
    return f"{node.get('name', '')} ({store.node_type(node)})"


def check(question: str, reasoned: ReasonedAnswer, patient_context_text: str) -> dict:
    """Scores each sentence of the Reasoner's answer against the
    accumulated, pruned KB context, flagging the answer 'weak' if any
    sentence's best-matching evidence scores below cfg.checker_threshold.
    Genuinely unverified end-to-end — see specs/v4.2/01's status note."""
    evidence = "\n\n".join(_node_text(n) for n in reasoned.citations) or patient_context_text
    model = _get_checker_model()
    sentences = _sentences(reasoned.text)
    unsupported: list[str] = []
    for sentence in sentences:
        score = model.predict([(evidence, sentence)])[0]
        if score < cfg.checker_threshold:
            unsupported.append(sentence)

    verdict = "weak" if unsupported else "pass"
    note = (
        f"{len(unsupported)} sentence(s) not confidently supported by the accumulated "
        "context." if unsupported else
        "Every sentence checked against the accumulated context."
    )
    return {"verdict": verdict, "unsupported": unsupported, "note": note}
