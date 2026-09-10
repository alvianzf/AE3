"""Traversal-loop logic, verified independent of any real LLM call: the
relevance judgment is mocked (a plain Python function passed as
judge_fn), and app.graph.store.fetch_hop_neighbors is mocked (no Neo4j
needed) — only GraphTraversalRetriever's own stopping/pruning logic is
under test here.

Run: python -m unittest tests.test_traversal -v
(stdlib unittest, not pytest — no new test dependency for one test file,
per this repo's "every dependency is permanent code" convention.)
"""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("NEBIUS_API_KEY", "test")

from app.patient.context import PatientContext
from app.retrieval.seed_search import SeedResult
from app.retrieval.traversal import GraphTraversalRetriever


def _patient() -> PatientContext:
    return PatientContext(
        client_id="c1", name="Test Patient", dob="1990-01-01", country="US",
        conditions=["hypothyroidism"], medications=["levothyroxine"],
    )


def _seed(*ids: str) -> SeedResult:
    return SeedResult(
        search_query="q",
        seed_chunk_ids=list(ids),
        seed_entity_ids=[],
        seed_records={i: {"id": i, "text": f"seed {i}", "document_title": "doc"} for i in ids},
    )


def _candidate(cid: str) -> dict:
    return {"id": cid, "labels": ["Chunk"], "text": f"text {cid}",
            "document_title": "doc", "grade": 8, "via": "MENTIONS"}


def _all_relevant(question, patient, accumulated, candidates):
    return [{"id": c["id"], "relevant": True, "reason": "matches"} for c in candidates]


def _all_irrelevant(question, patient, accumulated, candidates):
    return [{"id": c["id"], "relevant": False, "reason": "off-topic"} for c in candidates]


class TraversalStoppingTests(unittest.TestCase):
    def test_stops_when_frontier_empties(self):
        """Primary stopping condition: every branch gets pruned, no depth
        cap involved (max_depth is generous here on purpose)."""
        with patch("app.retrieval.traversal.store.fetch_hop_neighbors") as fetch:
            fetch.return_value = [_candidate("a"), _candidate("b")]
            retriever = GraphTraversalRetriever(
                max_depth=10, judge_fn=_all_irrelevant)
            result = retriever.retrieve("question", _patient(), _seed("seed1"))

        self.assertEqual(result.stopped_reason, "frontier_empty")
        self.assertEqual(result.depth_reached, 1)
        # The seed survives (it was never judged, only expanded from);
        # neither candidate does, since both were judged irrelevant.
        self.assertEqual({r["id"] for r in result.accumulated}, {"seed1"})
        fetch.assert_called_once()

    def test_stops_at_max_depth_even_with_live_frontier(self):
        """Circuit breaker: every hop finds relevant candidates forever,
        so only the depth cap can end this traversal."""
        with patch("app.retrieval.traversal.store.fetch_hop_neighbors") as fetch:
            fetch.side_effect = lambda frontier, visited, min_grade, limit: [
                _candidate(f"{'.'.join(sorted(frontier))}-child")
            ]
            retriever = GraphTraversalRetriever(max_depth=3, judge_fn=_all_relevant)
            result = retriever.retrieve("question", _patient(), _seed("seed1"))

        self.assertEqual(result.stopped_reason, "max_depth_reached")
        self.assertEqual(result.depth_reached, 3)
        self.assertEqual(fetch.call_count, 3)

    def test_stops_when_no_new_candidates(self):
        """A live frontier whose neighbors are all already visited (or
        simply has none) — distinct from frontier_empty, which happens
        after a hop that *did* return candidates but none were relevant."""
        with patch("app.retrieval.traversal.store.fetch_hop_neighbors") as fetch:
            fetch.return_value = []
            retriever = GraphTraversalRetriever(max_depth=10, judge_fn=_all_relevant)
            result = retriever.retrieve("question", _patient(), _seed("seed1"))

        self.assertEqual(result.stopped_reason, "no_new_candidates")
        self.assertEqual(result.depth_reached, 0)
        fetch.assert_called_once()

    def test_visited_set_dedups_across_hops(self):
        """A node judged on hop 1 must never be offered as a candidate
        again — fetch_hop_neighbors is trusted to honor the `visited` set
        it's passed, so this test asserts the retriever actually *grows*
        that set correctly hop over hop (including the irrelevant one,
        "b": visited-dedup applies regardless of the judgment, since
        pruning is about the next frontier, not about revisitability)."""
        calls: list[set[str]] = []

        def fetch(frontier, visited, min_grade, limit):
            calls.append(set(visited))
            if len(calls) == 1:
                return [_candidate("a"), _candidate("b")]
            if len(calls) == 2:
                return [_candidate("c")]
            return []

        with patch("app.retrieval.traversal.store.fetch_hop_neighbors", side_effect=fetch):
            # "b" is judged irrelevant on hop 1 (dies there); "a" and "c"
            # stay relevant, carrying the frontier to a 3rd hop where
            # fetch_hop_neighbors legitimately has nothing left to offer.
            def judge(question, patient, accumulated, candidates):
                return [{"id": c["id"], "relevant": c["id"] != "b", "reason": ""}
                        for c in candidates]

            retriever = GraphTraversalRetriever(max_depth=10, judge_fn=judge)
            result = retriever.retrieve("question", _patient(), _seed("seed1"))

        self.assertEqual(calls[0], {"seed1"})
        self.assertEqual(calls[1], {"seed1", "a", "b"})
        self.assertEqual(calls[2], {"seed1", "a", "b", "c"})
        self.assertEqual(result.stopped_reason, "no_new_candidates")
        self.assertEqual({r["id"] for r in result.accumulated}, {"seed1", "a", "c"})

    def test_path_log_records_every_judged_candidate(self):
        """Medical-safety requirement from the spec: every expansion and
        every prune must be traceable, not just the survivors."""
        with patch("app.retrieval.traversal.store.fetch_hop_neighbors") as fetch:
            fetch.side_effect = [[_candidate("a"), _candidate("b")], []]
            retriever = GraphTraversalRetriever(max_depth=10, judge_fn=_all_irrelevant)
            result = retriever.retrieve("question", _patient(), _seed("seed1"))

        self.assertEqual(len(result.path_log), 2)
        self.assertEqual({e.candidate_id for e in result.path_log}, {"a", "b"})
        self.assertTrue(all(not e.relevant for e in result.path_log))
        self.assertTrue(all(e.reason for e in result.path_log))


if __name__ == "__main__":
    unittest.main()
