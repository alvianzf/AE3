# 02 · Scope decisions carried over from the existing product

Two things the brief's schema/pipeline didn't mention, both decided
explicitly (asked and answered) rather than silently dropped, because
both are marketed, load-bearing safety features of the shipped product —
same treatment, same reasoning both times: don't let a from-scratch
architecture spec quietly delete a feature nobody decided to remove.

## Grading, carried forward onto `Document`

The brief's schema has no reliability-grade field. The existing product's
"you set the bar" pillar (`MIN_GRADE`, the grade slider,
`README.md`) is real and marketed. **Decision: `grade` lives on
`Document`, carried forward from the Reader's suggested grade / admin
overrides exactly as before.** `store.fetch_hop_neighbors()` enforces it
on every Chunk-type candidate at every hop (not just at seed time) — a
grade threshold a practitioner sets can't be bypassed by traversal
wandering into a low-graded document three hops out. Entity candidates
pass through un-filtered (an entity carries no clinical claim by itself —
see that function's docstring for the reasoning).

## The Checker, carried forward as a post-hoc classifier pass

The brief's five roles (Reader, KG-builder, Embedder, Answer Engine,
Reasoner) have no verification/anti-hallucination step. The existing
product's "an independent check challenges every answer" pillar
(`app/llm.py`'s old Checker, ported into [v4.2](../v4.2/README.md) as a
direct HHEM-2.1-Open classifier call) is also real and marketed.
**Decision: `app/reasoning/checker.py` runs after the Reasoner, scoring
each answer sentence against the accumulated, pruned context.** Same
bounded-retry pattern as before (one revision attempt on a "weak"
verdict, then ship whichever answer is better) — see
`app/main.py`'s `/api/me/consult` handler.

## What this means for cost/latency

Both additions are deliberately kept on the "cheap" side of the brief's
own cost model — grading is a pre-existing property lookup at every hop,
not an extra LLM call, and the Checker is a local classifier, not a chat
completion — so neither works against the brief's explicit split
("Answer Engine: keep this cheap and fast... Reasoner: called once per
query, this is where the expensive reasoning belongs").
