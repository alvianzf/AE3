"""Shadow-mode comparison: the existing two-stage graph-traversal pipeline
vs. the new agentic retrieval loop (app/retrieval/agentic.py), run on the
same real questions against a real patient, for the practitioner-judgment
comparison the architecture decision doc's Phase 1 calls for.

Not a production code path — a standalone script, same spirit as this
session's disposable-test-client production-verification scripts. Every
run logs an agentic row to core_store.retrieval_trajectories (continual-
learning logging starts from this script's first run, not later) and
prints a side-by-side diff for manual judgment: documents found, latency,
grounding verdict, and both answer texts in full.

Usage:
    PYTHONPATH=. python scripts/shadow_eval_agentic.py \\
        --practitioner-id <id> --client-id <id> \\
        --question "What markers indicate insulin resistance?" \\
        [--question "..." ...] [--min-grade 7] [--max-turns 6]

Run against a disposable test client (create it, run this, delete it in
a finally block) when there's no real patient to compare against yet —
same pattern used throughout this session's production verification.
"""
from __future__ import annotations

import argparse
import sys
import time

from app import core_store
from app.patient.context import get_patient_context
from app.reasoning import llm_checker, reasoner
from app.reasoning.citation_gate import check_grounding
from app.retrieval import agentic
from app.retrieval.traversal import GraphTraversalRetriever, two_stage_discover


def _run_current_pipeline(question: str, patient, min_grade: int) -> dict:
    t0 = time.monotonic()
    seed_result = two_stage_discover(question, patient, min_grade)
    retriever = GraphTraversalRetriever(min_grade=min_grade)
    traversal = retriever.retrieve(question, patient, seed_result)
    reasoned = reasoner.answer(question, patient, traversal)
    verdict = llm_checker.check(question, reasoned, patient.as_query_text())
    latency = time.monotonic() - t0
    documents = sorted({
        n.get("document_id") for n in traversal.accumulated if n.get("document_id")
    })
    return {
        "answer_text": reasoned.text, "documents": documents,
        "latency_s": round(latency, 1), "checker_verdict": verdict["verdict"],
    }


def _run_agentic_pipeline(question: str, patient, min_grade: int, max_turns: int) -> dict:
    t0 = time.monotonic()
    result = agentic.run(question, patient, min_grade, max_turns=max_turns)
    latency = time.monotonic() - t0
    if result.answer_text is None:
        # Found live, this session's first eval run: check_grounding([], {})
        # correctly returns "pass" for an answer with no claims to check —
        # but the eval was reusing that same "pass" when the loop hit
        # max_turns with NO answer at all (citations=[] either way), which
        # printed as a clean success for a run that actually produced
        # nothing. Distinct verdict so this failure mode is never silently
        # indistinguishable from a real pass.
        return {
            "answer_text": None, "documents": [], "latency_s": round(latency, 1),
            "turns_used": result.turns_used, "grounding_verdict": "no_answer_produced",
            "flagged": [],
        }
    grounding = check_grounding(result.citations, result.chunk_texts)
    documents = sorted({
        entry["output"].get("document_id")
        for entry in result.trace
        if isinstance(entry["output"], dict) and entry["output"].get("document_id")
    } | {
        r.get("document_id")
        for entry in result.trace
        for r in (entry["output"].get("results") or [])
        if r.get("document_id")
    })
    core_store.save_retrieval_trajectory(
        question=question, tool_calls=result.trace,
        cited_document_ids=sorted({c.get("chunk_id", "") for c in result.citations}),
        turns_used=result.turns_used, grounding_verdict=grounding["verdict"],
        total_latency_s=round(latency, 1), pipeline="agentic_shadow",
    )
    return {
        "answer_text": result.answer_text, "documents": documents,
        "latency_s": round(latency, 1), "turns_used": result.turns_used,
        "grounding_verdict": grounding["verdict"], "flagged": grounding["flagged"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--practitioner-id", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--question", action="append", required=True, dest="questions")
    parser.add_argument("--min-grade", type=int, default=7)
    parser.add_argument("--max-turns", type=int, default=6)
    args = parser.parse_args()

    patient = get_patient_context(args.practitioner_id, args.client_id)
    if patient is None:
        print(f"No patient found for client_id={args.client_id!r}", file=sys.stderr)
        return 1

    for question in args.questions:
        print(f"\n{'=' * 80}\nQuestion: {question}\n{'=' * 80}")

        current = _run_current_pipeline(question, patient, args.min_grade)
        print(f"\n--- Current (two-stage graph traversal) ---")
        print(f"documents: {len(current['documents'])}  latency: {current['latency_s']}s  "
              f"checker: {current['checker_verdict']}")
        print(current["answer_text"])

        agentic_result = _run_agentic_pipeline(question, patient, args.min_grade, args.max_turns)
        print(f"\n--- Agentic (shadow) ---")
        print(f"documents: {len(agentic_result['documents'])}  latency: {agentic_result['latency_s']}s  "
              f"turns: {agentic_result['turns_used']}  grounding: {agentic_result['grounding_verdict']}")
        if agentic_result["flagged"]:
            print(f"flagged citations: {agentic_result['flagged']}")
        print(agentic_result["answer_text"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
