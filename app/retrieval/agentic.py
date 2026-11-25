"""Agentic tool-driven retrieval — Phase 0+1 of the architecture decision
this session's research produced (4-way comparison against the existing
graph-traversal pipeline; decision doc archived in this session's
scratchpad as arch-decision-final.md). Instead of a fixed query-rewrite
-> seed -> judged-hop(s) -> answer pipeline, the Reasoner model gets its
own search tools and decides, turn by turn, whether it has enough
evidence to answer or needs to search more.

Shadow-mode only for this cut (scripts/shadow_eval_agentic.py) — not
wired into /api/me/consult's default path. See the plan's "What does NOT
change in this cut" section: the existing two-stage graph-traversal
pipeline (app/retrieval/traversal.py) stays the production default until
a real shadow-mode eval shows this path matches or beats it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..clients.llm_client import Role, get_client
from ..graph import store
from ..patient.context import PatientContext
from . import seed_search

AGENTIC_SYSTEM = (
    "You are a senior clinician answering a practitioner's question during "
    "a live consult, using tools to search a curated clinical knowledge "
    "library. You have no clinical knowledge of your own available here — "
    "only what the tools return.\n\n"
    "Search as many times as you actually need — a question only one "
    "source covers needs one search; a question that requires connecting "
    "findings across several different sources needs several searches, "
    "worded differently each time, not just one broad search repeated. "
    "Use find_similar on a chunk that's clearly relevant but incomplete to "
    "reach a related passage in a DIFFERENT document, the way a colleague "
    "would follow a citation to another source.\n\n"
    "Never fabricate — if nothing you found directly and specifically "
    "answers the question, call submit_answer saying plainly that you "
    "don't have anything on it, and stop there.\n\n"
    "When you call submit_answer, `citations` must list every chunk_id "
    "you actually relied on, each paired with the specific claim in your "
    "answer that chunk supports — the literal sentence/fact it backs, not "
    "a general topic match. Every clinical claim in `answer_text` must "
    "have a matching citation; a claim with none is a claim with no "
    "evidence."
)

_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "What to search the knowledge library for — can "
                           "be worded differently from the practitioner's "
                           "own question, and called more than once with "
                           "different wording to reach different sources.",
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}

_GET_DOCUMENT_SCHEMA = {
    "type": "object",
    "properties": {"document_id": {"type": "string"}},
    "required": ["document_id"],
    "additionalProperties": False,
}

_FIND_SIMILAR_SCHEMA = {
    "type": "object",
    "properties": {
        "chunk_id": {
            "type": "string",
            "description": "A chunk_id from an earlier search result to "
                           "find related passages for, typically in a "
                           "different document.",
        },
    },
    "required": ["chunk_id"],
    "additionalProperties": False,
}

_SUBMIT_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer_text": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chunk_id": {"type": "string"},
                    "supports": {
                        "type": "string",
                        "description": "The specific claim in answer_text "
                                       "this chunk backs, verbatim or "
                                       "near-verbatim.",
                    },
                },
                "required": ["chunk_id", "supports"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["answer_text", "citations"],
    "additionalProperties": False,
}

# Provider-neutral shape (Anthropic's own {"name", "description",
# "input_schema"} naming) — both app/clients/llm_client.py's and
# anthropic_client.py's chat_agentic() consume this same list, translating
# to their own wire format internally. See those methods' docstrings.
TOOLS = [
    {
        "name": "search",
        "description": "Search the clinical knowledge library for passages "
                       "relevant to a query. Returns up to 10 chunks with "
                       "their ids, document titles, trust grades, and text.",
        "input_schema": _SEARCH_SCHEMA,
    },
    {
        "name": "get_document",
        "description": "Fetch a document's full text by id, when a single "
                       "chunk from it isn't enough context.",
        "input_schema": _GET_DOCUMENT_SCHEMA,
    },
    {
        "name": "find_similar",
        "description": "Find chunks related to a specific chunk you've "
                       "already seen, often in a different document — use "
                       "this to follow a connection to another source.",
        "input_schema": _FIND_SIMILAR_SCHEMA,
    },
    {
        "name": "submit_answer",
        "description": "Submit your final answer, once you have enough "
                       "evidence (or have confirmed there's nothing "
                       "relevant). Ends the search.",
        "input_schema": _SUBMIT_ANSWER_SCHEMA,
    },
]

_SEARCH_TOP_K = 10
_GET_DOCUMENT_MAX_CHUNKS = 20
_FIND_SIMILAR_TOP_K = 5


def _chunk_summary(r: dict) -> dict:
    """What a tool result actually hands the model — trimmed to what it
    needs to decide whether to look further, not the full ingest-time
    record shape store.py's queries return."""
    return {
        "chunk_id": r["id"], "document_id": r.get("document_id"),
        "document_title": r.get("document_title"), "grade": r.get("grade"),
        "text": r.get("text"),
    }


@dataclass
class AgenticTools:
    """Bound to one question's patient/scope context — make_tool_fn()
    closes over this, same shape every other per-consult retrieval
    function already takes (folder/topic/weights/accessible_private_ids),
    just carried as one object instead of several separate closure
    variables, since this function set is bigger than seed_search.seed()'s
    own."""
    patient: PatientContext
    min_grade: int
    weights: dict[str, int] = field(default_factory=dict)
    accessible_private_ids: set[str] = field(default_factory=set)
    folder: str = ""
    topic: str = ""


def _search(tools: AgenticTools, query: str) -> dict:
    result = seed_search.seed(
        query, tools.patient, tools.min_grade, top_k=_SEARCH_TOP_K,
        weights=tools.weights, accessible_private_ids=tools.accessible_private_ids,
        folder=tools.folder, topic=tools.topic,
    )
    chunks = [result.seed_records[cid] for cid in result.seed_chunk_ids]
    if not chunks:
        return {"results": [], "note": "No passages matched this query."}
    return {"results": [_chunk_summary(c) for c in chunks]}


def _get_document(tools: AgenticTools, document_id: str) -> dict:
    doc = store.document_text(document_id)
    if doc is None:
        return {"error": f"No document with id {document_id!r}."}
    passages = doc["passages"][:_GET_DOCUMENT_MAX_CHUNKS]
    return {
        "document_id": document_id, "title": doc.get("title"), "grade": doc.get("grade"),
        "chunks": [{"chunk_id": f"{document_id}:{p['chunk_index']}", "text": p["text"]}
                  for p in passages],
    }


def _find_similar(tools: AgenticTools, chunk_id: str) -> dict:
    # fetch_hop_neighbors-style re-filter: a neighbor reached via the
    # vector index has had no privacy/scope check applied to it yet,
    # unlike a `search()` result which already went through seed_search's
    # own filter — same reasoning app/graph/store.py's fetch_hop_neighbors
    # docstring gives for re-checking at every hop, not just the seed.
    neighbors = [
        n for n in store.neighbors_by_embedding(chunk_id, _FIND_SIMILAR_TOP_K)
        if (not n.get("is_private") or n.get("document_id") in tools.accessible_private_ids)
        and store.in_scope(n, tools.folder, tools.topic)
    ]
    if not neighbors:
        return {"results": [], "note": "Nothing related found."}
    return {"results": [_chunk_summary(n) for n in neighbors]}


def make_tool_fn(tools: AgenticTools):
    """Returns the tool_fn(name, input) -> dict callable chat_agentic()
    calls — a thin dispatcher over the three real tools; submit_answer is
    the loop's own terminal case and never reaches here (both client
    implementations intercept it directly before calling tool_fn — see
    chat_agentic's docstring)."""
    def _dispatch(name: str, tool_input: dict) -> dict:
        if name == "search":
            return _search(tools, tool_input.get("query", ""))
        if name == "get_document":
            return _get_document(tools, tool_input.get("document_id", ""))
        if name == "find_similar":
            return _find_similar(tools, tool_input.get("chunk_id", ""))
        return {"error": f"Unknown tool: {name!r}"}
    return _dispatch


_ZERO_USAGE = {"input_tokens": 0, "output_tokens": 0}


@dataclass
class AgenticResult:
    answer_text: str | None
    citations: list[dict]
    trace: list[dict]
    chunk_texts: dict[str, str]
    turns_used: int
    usage: dict = field(default_factory=lambda: dict(_ZERO_USAGE))


def run(question: str, patient: PatientContext, min_grade: int,
       weights: dict[str, int] | None = None,
       accessible_private_ids: set[str] | None = None,
       folder: str = "", topic: str = "", max_turns: int = 6) -> AgenticResult:
    """Runs the full agentic retrieval loop for one question. Shadow-mode
    entry point (scripts/shadow_eval_agentic.py) — not called from
    app/main.py's consult route in this cut.

    `chunk_texts` is built from the tool-call trace itself — exactly what
    the model actually saw, not a separate re-fetch — so
    app/reasoning/citation_gate.py's check runs against the same evidence
    the agent had, never a possibly-drifted later read of the same chunk.
    """
    tools = AgenticTools(
        patient=patient, min_grade=min_grade, weights=weights or {},
        accessible_private_ids=accessible_private_ids or set(), folder=folder, topic=topic,
    )
    prompt = f"Patient context:\n{patient.as_query_text()}\n\nQuestion: {question}"
    submit, trace, usage = get_client(Role.REASONER).chat_agentic(
        AGENTIC_SYSTEM, prompt, TOOLS, make_tool_fn(tools), max_turns=max_turns,
    )
    chunk_texts: dict[str, str] = {}
    for entry in trace:
        for r in (entry["output"].get("results") or entry["output"].get("chunks") or []):
            cid = r.get("chunk_id")
            if cid and r.get("text"):
                chunk_texts[cid] = r["text"]
    if submit is None:
        return AgenticResult(
            answer_text=None, citations=[], trace=trace, chunk_texts=chunk_texts,
            turns_used=max_turns, usage=usage,
        )
    return AgenticResult(
        answer_text=submit.get("answer_text", ""), citations=submit.get("citations") or [],
        trace=trace, chunk_texts=chunk_texts, turns_used=len(trace) + 1, usage=usage,
    )
