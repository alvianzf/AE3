"""Final step: the pruned, accumulated KB context + raw patient data go to
KIMI-K3 (Role.REASONER) once per query — this is where the expensive
reasoning belongs, per the brief; every earlier LLM call in the pipeline
(Reader/KG-builder at ingest time, Answer Engine's seed-query-forming and
per-hop relevance judging at query time) is deliberately cheap and fast.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..clients.llm_client import Role, get_client
from ..graph import store
from ..patient.context import PatientContext
from ..retrieval.traversal import TraversalResult

# moonshotai/Kimi-K3's hidden chain-of-thought pass costs 30-120s+ per
# call with no visible quality difference on this app's prompts (found
# live, 2026-09-14) — disabled for every Reasoner call. Harmless to leave
# on unconditionally even now that the default REASONER_MODEL is Qwen3-235B
# (config.py) — a non-reasoning model with no "thinking" field of its own
# just ignores this extra_body key (confirmed live), so this stays applied
# regardless of which model REASONER_MODEL actually points at, including a
# future switch back to Kimi-K3 on a dedicated EU endpoint.
_NO_THINKING = {"thinking": {"type": "disabled"}}

REASONER_SYSTEM = (
    "You are a senior clinician advising a practitioner during a consultation — "
    "a knowledgeable colleague speaking from what you know, not a search tool "
    "reporting results. Never describe yourself as searching, looking something "
    "up, or consulting a database/library/knowledge base — speak in first person, "
    "the way a colleague states what they know or admits they don't, not the way "
    "a system reports what a query returned.\n\n"
    "What you 'know' is strictly bounded by the accumulated context below and "
    "the patient's own data — you have no other knowledge available to you "
    "here — but that boundary is a fact about your input, not something to "
    "narrate to the reader.\n\n"
    "Rules:\n"
    "- Cite the chunk or entity behind each clinical point inline, as [K1], [K2].\n"
    "  A claim with no citation is a claim with no evidence — don't make it.\n"
    "- A passage that is merely topic-adjacent does NOT cover the question. If no "
    "passage directly and specifically addresses what was asked, do not construct "
    "an answer by inference, extrapolation, or general clinical reasoning from "
    "nearby context — that is fabrication even if it sounds plausible. In that "
    "case the entire response is one short, direct sentence: that you don't have "
    "anything on it. Stop there. Do not describe what the retrieved context does "
    "cover instead, do not explain why, do not say what would be needed to answer "
    "it — every one of those is padding around 'no' and reads as an excuse. If "
    "there's nothing, say there's nothing.\n"
    "- Never fill a gap from general knowledge, training data, or what's usually "
    "true in medicine. If it isn't in the context below, it isn't in this answer.\n"
    "- Weigh the patient's specific conditions, medications, and labs explicitly "
    "where they matter — a general answer that ignores what's already in front of "
    "you about this patient is not the answer this patient needs.\n"
    "- Never write a placeholder in brackets (like '[patient data]', '[insert "
    "value]', '[age]') standing in for a real value. Either use the actual value "
    "given in the patient context below, or, if it isn't recorded, say plainly "
    "that it isn't recorded — never leave a template slot unfilled in the output.\n"
    "- Be terse and clinical, not flowery: short sentences, no preamble, no "
    "restating the question, no hedging filler.\n\n"
    "Structure the answer in Markdown with exactly these sections, omitting a "
    "section entirely (heading included) if it has nothing to say:\n"
    "## Answer\n"
    "The clinical answer itself, as concisely as the context allows.\n"
    "## Confirm with patient\n"
    "A short bullet list of what to ask or verify with this patient before "
    "acting on the answer — only include this if something genuinely needs "
    "confirming, not as a rote checklist.\n"
    "## Next steps\n"
    "A short bullet list of concrete next actions for the practitioner."
)


@dataclass
class ReasonedAnswer:
    text: str
    usage: dict
    citations: list[dict]  # the accumulated records actually shown to the model


def _label(node: dict) -> str:
    if store.is_chunk(node):
        return f"(source: {node.get('document_title', 'unknown')}) {node['text']}"
    return f"(entity, {store.node_type(node)}: {node.get('name', node.get('id'))})"


def answer(question: str, patient: PatientContext, traversal: TraversalResult,
          unsupported: list[str] | None = None) -> ReasonedAnswer:
    """`unsupported` is only passed on the one bounded revision retry
    (mirrors the pre-existing Checker retry pattern) — the Checker's own
    list of sentences it couldn't ground in the accumulated context. The
    instruction is strictly "ground it or drop it": no new context is
    supplied, so a flagged sentence can only be tied to context already
    given, or removed."""
    if traversal.accumulated:
        block = "\n\n".join(
            f"[K{i + 1}] {_label(node)}" for i, node in enumerate(traversal.accumulated)
        )
    else:
        block = "(the traversal found nothing surviving relevance pruning)"
    revision_block = ""
    if unsupported:
        claims = "\n".join(f"- {c}" for c in unsupported)
        revision_block = (
            "\n\nAn independent check of your previous draft found these sentences "
            f"not actually supported by the context above:\n{claims}\n\n"
            "Write a new answer. For each of those, either tie it explicitly to "
            "context that genuinely supports it, or remove it — do not keep it by "
            "rephrasing it more vaguely. Do not introduce new claims the context "
            "doesn't cover either."
        )
    prompt = (
        f"Patient context:\n{patient.as_query_text()}\n\n"
        f"Accumulated knowledge-base context:\n---\n{block}\n---\n\n"
        f"Practitioner's question: {question}{revision_block}"
    )
    text, usage = get_client(Role.REASONER).chat_text(
        REASONER_SYSTEM, prompt, max_tokens=100_000, extra_body=_NO_THINKING)
    return ReasonedAnswer(text=text, usage=usage, citations=traversal.accumulated)


SUMMARY_SYSTEM = (
    "Write a short session summary for a patient's clinical record: what was "
    "asked, what the assistant advised, and anything the next practitioner should "
    "know. Three or four sentences, plain clinical prose, no headings."
)


def summarize_session(transcript: str) -> str:
    text, _usage = get_client(Role.REASONER).chat_text(
        SUMMARY_SYSTEM, transcript, max_tokens=100_000, extra_body=_NO_THINKING)
    return text
