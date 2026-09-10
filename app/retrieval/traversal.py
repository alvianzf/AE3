"""GraphTraversalRetriever: iterative graph traversal with LLM-judged
relevance pruning, starting from vector-search seed chunks/entities.

Each hop: fetch unvisited neighbors of the current frontier (one Cypher
query, store.fetch_hop_neighbors), batch them into one relevance-judgment
call against the *original question + patient context + what's
accumulated so far* (not just the immediate parent — a candidate can be
relevant because of something found three hops back), then relevant
candidates become next hop's frontier and irrelevant ones die there.

Stops when the frontier goes empty (every live branch got pruned or ran
out of new neighbors) — the primary, intended termination. max_depth is a
circuit breaker against runaway cost/depth, not the primary stopping
logic (config.py's traversal_max_depth, default 5).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..clients.llm_client import Role, get_client
from ..config import get_config
from ..graph import store
from ..patient.context import PatientContext
from .seed_search import SeedResult

cfg = get_config()

RELEVANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "judgments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "The candidate's id, verbatim."},
                    "relevant": {"type": "boolean"},
                    "reason": {"type": "string", "description": "One short sentence."},
                },
                "required": ["id", "relevant", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["judgments"],
    "additionalProperties": False,
}

RELEVANCE_SYSTEM = (
    "You judge whether newly-discovered graph nodes are still relevant to a "
    "clinical question, for this specific patient, given what's already been "
    "gathered.\n\n"
    "A node is relevant if it would help answer the question for this patient — "
    "including a node that matters *because of* this patient's specific "
    "conditions/medications/labs, even if it wouldn't matter for a different "
    "patient (a drug-interaction question needs you to say 'relevant' to a node "
    "about an interaction with something this patient is already taking, even "
    "if the question itself never named that medication).\n\n"
    "Judge every candidate independently and return one judgment per candidate "
    "id, in the same ids you were given."
)


def _candidate_label(c: dict) -> str:
    if store.is_chunk(c):
        doc = c.get("document_title", "unknown source")
        return f"[chunk from {doc}] {c['text'][:400]}"
    return f"[entity: {store.node_type(c)}] {c.get('name', c['id'])}"


def llm_judge_relevance(question: str, patient: PatientContext,
                        accumulated: list[dict], candidates: list[dict]) -> list[dict]:
    """Default judge_fn: one batched Role.ANSWER_ENGINE call per hop.

    Returns a list aligned to `candidates` (same order, same length) —
    GraphTraversalRetriever._run_hop() depends on that alignment, not on
    matching the returned `id` back up (a model dropping/reordering an id
    would otherwise silently desync accumulated state from what was
    actually judged).
    """
    if not candidates:
        return []
    accumulated_text = "\n".join(
        f"- {_candidate_label(a)}" for a in accumulated[-30:]  # bounded, not the whole history verbatim
    ) or "(nothing gathered yet)"
    candidates_text = "\n".join(
        f"{c['id']}: {_candidate_label(c)}" for c in candidates
    )
    prompt = (
        f"Patient context:\n{patient.as_query_text()}\n\n"
        f"Question: {question}\n\n"
        f"Already gathered (for context, not to be re-judged):\n{accumulated_text}\n\n"
        f"New candidates to judge:\n{candidates_text}"
    )
    result, _usage = get_client(Role.ANSWER_ENGINE).chat_json(
        RELEVANCE_SYSTEM, prompt, RELEVANCE_SCHEMA, max_tokens=4000)
    by_id = {j["id"]: j for j in result["judgments"]}
    # A model that drops an id from its response is treated as "not
    # relevant, no reason given" rather than crashing the hop — a partial
    # judgment failure shouldn't take down the whole traversal, but it's
    # logged in the returned reason so it's visible in the path log, not
    # silently indistinguishable from a real negative judgment.
    return [
        by_id.get(c["id"], {"relevant": False, "reason": "no judgment returned by model"})
        for c in candidates
    ]


@dataclass
class HopLogEntry:
    hop: int
    candidate_id: str
    candidate_label: str
    relevant: bool
    reason: str


@dataclass
class TraversalResult:
    accumulated: list[dict]
    path_log: list[HopLogEntry]
    depth_reached: int
    stopped_reason: str  # "frontier_empty" | "max_depth_reached" | "no_new_candidates"


JudgeFn = Callable[[str, PatientContext, list[dict], list[dict]], list[dict]]


class GraphTraversalRetriever:
    def __init__(self, min_grade: int | None = None, max_depth: int | None = None,
                max_candidates_per_hop: int | None = None,
                judge_fn: JudgeFn | None = None,
                weights: dict[str, int] | None = None):
        self.min_grade = cfg.min_grade if min_grade is None else min_grade
        self.max_depth = cfg.traversal_max_depth if max_depth is None else max_depth
        self.max_candidates_per_hop = (
            cfg.traversal_max_candidates_per_hop if max_candidates_per_hop is None
            else max_candidates_per_hop
        )
        # A practitioner's own per-document grade override (never the
        # shared admin grade) — threaded through to every hop's
        # store.fetch_hop_neighbors() call so a down-weighted source
        # can't re-enter via a later hop just because that hop only
        # checked the shared grade.
        self.weights = weights or {}
        # Injectable so the stopping/pruning logic can be verified with a
        # deterministic fake judge_fn, independent of any real LLM call —
        # see tests/test_traversal.py.
        self.judge_fn = judge_fn or llm_judge_relevance

    def retrieve(self, question: str, patient: PatientContext,
                seed_result: SeedResult) -> TraversalResult:
        frontier = list(dict.fromkeys([*seed_result.seed_chunk_ids, *seed_result.seed_entity_ids]))
        visited: set[str] = set(frontier)
        accumulated: dict[str, dict] = {fid: seed_result.seed_records[fid] for fid in frontier}
        path_log: list[HopLogEntry] = []

        depth = 0
        stopped_reason = "frontier_empty"
        while frontier:
            if depth >= self.max_depth:
                stopped_reason = "max_depth_reached"
                break

            candidates = store.fetch_hop_neighbors(
                frontier, visited, self.min_grade, self.max_candidates_per_hop,
                weights=self.weights)
            if not candidates:
                stopped_reason = "no_new_candidates"
                break

            depth += 1
            judgments = self.judge_fn(question, patient, list(accumulated.values()), candidates)
            next_frontier: list[str] = []
            for cand, verdict in zip(candidates, judgments):
                cid = cand["id"]
                visited.add(cid)
                relevant = bool(verdict.get("relevant"))
                path_log.append(HopLogEntry(
                    hop=depth, candidate_id=cid, candidate_label=_candidate_label(cand),
                    relevant=relevant, reason=verdict.get("reason", ""),
                ))
                if relevant:
                    accumulated[cid] = cand
                    next_frontier.append(cid)
            frontier = next_frontier
            if not frontier:
                stopped_reason = "frontier_empty"

        return TraversalResult(
            accumulated=list(accumulated.values()), path_log=path_log,
            depth_reached=depth, stopped_reason=stopped_reason,
        )
