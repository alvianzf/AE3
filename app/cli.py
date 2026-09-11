"""Entrypoint for ingestion and end-to-end querying, outside the FastAPI
app — useful for testing the pipeline against real documents/questions
without going through HTTP.

    python -m app.cli ingest path/to/source.txt --kind text --origin "..."
    python -m app.cli query <practitioner_id> <client_id> "question here"

Deliberately minimal (argparse, no framework) — this is a dev/ops tool,
not a user-facing surface.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def cmd_ingest(args: argparse.Namespace) -> None:
    from .graph.schema import ensure_schema
    from .ingestion.pipeline import ingest

    ensure_schema()
    text = args.file.read_text()
    try:
        doc = ingest(text=text, filename=args.file.name, kind=args.kind, origin=args.origin)
    except ValueError as exc:
        print(f"Ingestion skipped: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps({"id": doc["id"], "title": doc["title"], "grade": doc["grade"],
                      "chunks": doc["chunks"]}, indent=2))


def cmd_query(args: argparse.Namespace) -> None:
    from .patient.context import get_patient_context
    from .reasoning.reasoner import answer as reason_answer
    from .retrieval.seed_search import seed
    from .retrieval.traversal import GraphTraversalRetriever

    patient = get_patient_context(args.practitioner_id, args.client_id)
    if patient is None:
        print("No such client for that practitioner.", file=sys.stderr)
        raise SystemExit(1)

    from .config import get_config
    cfg = get_config()

    seed_result = seed(args.question, patient, min_grade=cfg.min_grade)
    logging.info("seed: query=%r, %d seed nodes",
                seed_result.search_query,
                len(seed_result.seed_chunk_ids) + len(seed_result.seed_entity_ids))

    retriever = GraphTraversalRetriever()
    traversal = retriever.retrieve(args.question, patient, seed_result)
    logging.info("traversal: stopped=%s, depth=%d, accumulated=%d nodes, %d hop judgments",
                traversal.stopped_reason, traversal.depth_reached,
                len(traversal.accumulated), len(traversal.path_log))
    if args.verbose:
        for entry in traversal.path_log:
            mark = "KEEP" if entry.relevant else "DROP"
            logging.info("  hop %d [%s] %s — %s", entry.hop, mark,
                        entry.candidate_id, entry.reason)

    reasoned = reason_answer(args.question, patient, traversal)
    print(reasoned.text)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="ingest one source file")
    p_ingest.add_argument("file", type=Path)
    p_ingest.add_argument("--kind", default="text")
    p_ingest.add_argument("--origin", default="cli")
    p_ingest.set_defaults(func=cmd_ingest)

    p_query = sub.add_parser("query", help="run one question end-to-end")
    p_query.add_argument("practitioner_id")
    p_query.add_argument("client_id")
    p_query.add_argument("question")
    p_query.add_argument("--verbose", action="store_true",
                         help="print every hop's keep/drop judgment")
    p_query.set_defaults(func=cmd_query)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
