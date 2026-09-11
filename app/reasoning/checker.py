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
    download cost the first time check() (or ping()) actually runs."""
    global _checker_model
    if _checker_model is None:
        from transformers import AutoModelForSequenceClassification
        _checker_model = AutoModelForSequenceClassification.from_pretrained(
            cfg.checker_model, trust_remote_code=True)
    return _checker_model


def is_loaded() -> bool:
    """True once a prior check() (or ping()) has actually loaded the
    classifier into this process — used by ping() to decide whether it's
    safe to run a cheap inference check or whether doing so would first
    trigger a slow, network-dependent model download."""
    return _checker_model is not None


def ping() -> dict:
    """Report the Checker's status without ever blocking a health check
    on a cold model download.

    If the model is already loaded (a real check() has run in this
    process), runs one trivial (premise, hypothesis) scoring call to
    confirm it can still do inference, not just that it once loaded.
    If it isn't loaded yet, reports that plainly rather than forcing the
    download inline — HHEM-2.1-Open is hundreds of MB and its first load
    can take minutes on a slow connection; a monitoring endpoint hanging
    that long (or timing out) on every check before the first real
    consult would be worse than an honest "not loaded yet."
    """
    if not is_loaded():
        return {"loaded": False, "note": "not loaded yet — loads on the first real check() call"}
    model = _get_checker_model()
    model.predict([("The patient takes levothyroxine.", "The patient takes levothyroxine.")])
    return {"loaded": True}


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def _node_text(node: dict) -> str:
    if store.is_chunk(node):
        return node["text"]
    return f"{node.get('name', '')} ({store.node_type(node)})"


def check(question: str, reasoned: ReasonedAnswer, patient_context_text: str) -> dict:
    """Scores each sentence of the Reasoner's answer against its own
    best-matching individual citation, flagging the answer 'weak' if a
    sentence's best match still scores below cfg.checker_threshold.

    Deliberately per-citation, not one merged blob of every citation
    concatenated together: scoring against a blob lets an unrelated but
    topically-similar sentence elsewhere in the blob paper over a claim
    that no single source actually supports — exactly the failure mode
    this check exists to catch. Genuinely unverified end-to-end — see
    specs/v4.2/01's status note.

    `patient_context_text` is always one of the evidence candidates, not
    just a fallback for zero citations — a claim about the patient's own
    labs/history is legitimately supported by the patient record alone,
    never needing a library citation (the pre-v5 Checker's own rule).
    Checking such a claim only against cited library chunks — which
    don't mention this patient at all — would flag it "unsupported" on
    essentially every consult that cites anything.
    """
    evidence_texts = [_node_text(n) for n in reasoned.citations] + [patient_context_text]
    model = _get_checker_model()
    sentences = _sentences(reasoned.text)
    if not sentences:
        return {"verdict": "pass", "unsupported": [], "note": "Nothing to check."}

    # One batched predict() call for every (evidence, sentence) pair
    # rather than one call per sentence (or per sentence-per-citation) —
    # keeps this cheap regardless of how many sources were cited.
    pairs = [(ev, s) for s in sentences for ev in evidence_texts]
    scores = model.predict(pairs)
    per_evidence = len(evidence_texts)

    unsupported: list[str] = []
    for i, sentence in enumerate(sentences):
        sentence_scores = scores[i * per_evidence:(i + 1) * per_evidence]
        if max(sentence_scores) < cfg.checker_threshold:
            unsupported.append(sentence)

    verdict = "weak" if unsupported else "pass"
    note = (
        f"{len(unsupported)} sentence(s) not confidently supported by any single cited "
        "source." if unsupported else
        "Every sentence checked against its cited sources."
    )
    return {"verdict": verdict, "unsupported": unsupported, "note": note}
