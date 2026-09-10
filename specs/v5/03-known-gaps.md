# 03 · Known gaps and follow-up work

Flagged deliberately, not discovered later — each of these was a real
scoping call made under time pressure while implementing this, not an
oversight found in review.

## The Embedder's output has no consumer yet

`llm.embed_passages()`-equivalent (`LLMClient.embed()` via
`Role.EMBEDDER`) runs at ingest time and writes into a Neo4j vector index
(`schema.py`). **Nothing reads it back.** The recommended consumer — a
semantic-recall booster for the retrieval planner when graph-based
traversal comes up short, still grade-filtered — is decided but not
wired into `retrieval/traversal.py`. Reasoning: that touches the live
consult path with no way to verify against a real Neo4j instance here,
and a mistake there degrades every clinical answer silently. The write
path alone is safe to ship (additive, nothing depends on it yet).

## The consult UI's `t.librarian` block will render nothing

`(practitioner)/practitioner/consult/+page.svelte` has a
`{#if t.librarian}...{/if}` block showing "how the librarian chose."
`/api/me/consult`'s `result` event no longer has a `librarian` key (the
new shape is `seed_search`/`traversal` — see the endpoint for the actual
fields). The `{#if}` guard means this degrades gracefully (nothing
renders, no crash) rather than breaking, but the practitioner-facing
"why did it choose this" explanation is gone from the UI until that panel
is rewritten to read `traversal.path`, which carries strictly more detail
than the old `librarian` block did (every hop's keep/drop and why, not
just the initially-opened source list). Not done here — a frontend
change, out of scope for this backend rewrite pass.

## `history` (multi-turn consult context) is folded into the question text

The old pipeline threaded `history` as an explicit parameter through
`select_sources()`/`question_concepts()`/`answer()`. The new
`seed_search.form_search_query()`, `traversal.llm_judge_relevance()`, and
`reasoner.answer()` don't each take a `history` parameter yet —
`app/main.py`'s consult handler folds the last 6 turns into the question
string it passes to all three instead. Functionally preserves multi-turn
continuity; architecturally it's a stopgap. Threading `history` as a real
parameter through all three call sites is straightforward follow-up, not
done here under time pressure.

## `store.merge_entities()` requires APOC

Arbitrary-typed relationship redirection during entity-merge dedup can't
be expressed in plain Cypher (a relationship type isn't a runtime value
without APOC's `apoc.merge.relationship`). Admin-only, off the ingestion/
retrieval hot path, so a missing-APOC failure here is loud and low-stakes
— but real, and unverified against the actual target Neo4j instance.

## Per-hop relevance-judgment token usage isn't tracked

`retrieval/traversal.py`'s `llm_judge_relevance()` doesn't return its
usage back through `TraversalResult`, so `/api/me/consult`'s
`total_input_tokens`/`total_output_tokens` undercounts — every hop's
judgment call spends real tokens that never reach that total. Flagged in
`app/main.py`'s consult handler with a comment; not fixed here.

## Unverified, same caveat as v4.2

Exact Nebius catalog model-ID strings, HHEM-2.1-Open's real hosting/call
signature, `EMBEDDING_DIMENSIONS`'s match to Qwen3-Embedding-8B's actual
output size, and Neo4j's vector/full-text index Cypher syntax against the
actual target Neo4j version — none of these have been checked against a
real deployment. See [v4.2/01](../v4.2/01-nebius-provider-swap.md)'s
equivalent list; the same category of risk applies here, compounded by
an entirely new retrieval algorithm on top.
