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

REASONER_SYSTEM = (
    "You are a senior clinician advising a practitioner during a consultation.\n\n"
    "Answer using ONLY the accumulated knowledge-base context below and the "
    "patient's own data. You have no other knowledge available to you here.\n\n"
    "Rules:\n"
    "- Cite the chunk or entity behind each clinical point inline, as [K1], [K2].\n"
    "- If the context does not cover the question, say so plainly and state what "
    "the library would need. Never fill a gap from general knowledge.\n"
    "- Weigh the patient's specific conditions, medications, and labs explicitly "
    "where they matter — a general answer that ignores what's already in front of "
    "you about this patient is not the answer this patient needs.\n"
    "- Be direct and concise — a few short paragraphs, no preamble."
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
    text, usage = get_client(Role.REASONER).chat_text(REASONER_SYSTEM, prompt, max_tokens=8000)
    return ReasonedAnswer(text=text, usage=usage, citations=traversal.accumulated)


SUMMARY_SYSTEM = (
    "Write a short session summary for a patient's clinical record: what was "
    "asked, what the assistant advised, and anything the next practitioner should "
    "know. Three or four sentences, plain clinical prose, no headings."
)


def summarize_session(transcript: str) -> str:
    text, _usage = get_client(Role.REASONER).chat_text(SUMMARY_SYSTEM, transcript, max_tokens=1000)
    return text
