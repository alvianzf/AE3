# 01 · Retrieval latency follow-up

Produced 2026-09-14, same session as the `TRAVERSAL_MAX_CANDIDATES_PER_HOP`
fix (20→5, dropped the required `reason` field) that cut a real
seed+traversal call from 94.64s to 9.93s. The user asked what else could
push retrieval speed further. Five candidate levers were tested live
against production (real Nebius credentials, real Neo4j data, three
different real questions — not just the "metformin and PCOS" question
prior timing in this session used).

**Bottom line: not much is left.** The candidate-cap fix already captured
the large, reliable win. What remains is dominated by Nebius's own
per-call latency variance (largely outside this app's control) and one
small, real, unfixed Neo4j cost.

## 1. Skipping `form_search_query()` — not worth it

Tested embedding the raw practitioner question directly instead of
paying for the LLM call that reformulates it (`app/retrieval/
seed_search.py`'s `form_search_query()`, ~0.65-4.06s across three
questions).

| Question | form_search_query | embed(LLM query) | embed(raw question) | seed overlap (Jaccard) |
|---|---|---|---|---|
| metformin/PCOS | 4.06s | 9.49s | 2.94s | 0.44 |
| shift-worker circadian | 0.65s | 2.03s | 3.34s | 0.52 |
| sleep supplements | 2.16s | 0.11s | 0.08s | 0.53 |

Two problems with skipping it. First, **the time isn't reliably there to
save** — Embedder latency varies so much per call (0.08s to 9.49s
observed, no clear driver) that which query gets embedded barely
matters next to that variance; the raw question was *slower* to embed
than the LLM-formed one in one of three trials. Second, **the seed
results genuinely differ** — only 44-53% overlap between the two query
choices. That's not noise, it's the LLM-formed query doing its
documented job (conditioning the search on the patient's own
conditions/medications/labs, not just the question's words —
`seed_search.py`'s own module docstring). Skipping it would trade real
retrieval quality for savings that don't reliably materialize.

## 2. Neo4j query costs — mostly negligible, one real exception

Timed in isolation (embedding/LLM calls excluded):

| Query | Time |
|---|---|
| `seed_chunks_by_vector` | 0.02-0.03s |
| `seed_chunks_by_fulltext` | 0.01-0.02s |
| `entities_mentioned_by_chunks` | 0.37s |
| `fetch_hop_neighbors` (one hop, real frontier) | **1.33s** |

The seed-phase queries are non-issues. `fetch_hop_neighbors` — run once
per traversal hop, separate from and in addition to that hop's LLM judge
call — is a real, fixed-ish cost that multiplies by hop count (4-5 hops
observed elsewhere this session → ~5-6s of pure Neo4j overhead across a
traversal, on top of the LLM time). Not fixed here; a candidate for a
follow-up (check the query plan / whether an index covers `neighbor.id`
and the `visited_ids` exclusion efficiently at the graph's current
size). Separately: Neo4j flags `db.index.vector.queryNodes` as
deprecated in favor of its `SEARCH` syntax, but that call was measured
at 0.02-0.03s here — a future-compatibility item, not a current latency
one.

## 3. `TRAVERSAL_SEED_TOP_K` — no reliable direction

Compared `top_k=5` vs `top_k=10` (default) across three questions:

| Question | top_k=5 traversal | top_k=10 traversal |
|---|---|---|
| metformin/PCOS | 38.97s (depth 5, max_depth_reached) | 33.64s (depth 4) |
| shift-worker circadian | 7.86s (depth 1) | 6.83s (depth 1) |
| sleep supplements | 5.19s (depth 1) | 4.62s (depth 1) |

Lower `top_k` was **slower** in every trial here, not faster — a smaller
initial seed set means fewer strong early hits, so the traversal explores
more before the frontier naturally empties. Not a lever worth pulling in
the direction that seems intuitive; if anything the data points the
other way, though three trials isn't enough to call that a confirmed
effect either.

## 4. `TRAVERSAL_MAX_DEPTH` — mostly moot after the candidate-cap fix

Compared `max_depth` of 2, 3, and 5 (current default) on two questions,
using the same seed each time:

| Question | depth=2 | depth=3 | depth=5 |
|---|---|---|---|
| metformin/PCOS | 12.08s (hit cap) | 15.64s (frontier_empty @ 3) | 13.16s (frontier_empty @ 3) |
| shift-worker circadian | 5.25s (frontier_empty @ 1) | 8.12s (frontier_empty @ 1) | 4.97s (frontier_empty @ 1) |

With the candidate-cap fix already in place, most traversals now stop
naturally (`frontier_empty`) at depth 1-3, well short of `max_depth=5` —
lowering the ceiling further only helps the occasional genuinely broad
question that still reaches it (like the `top_k` test's outlier above,
38.97s at depth 5). It doesn't move the typical case, which no longer
reaches the ceiling regardless of where it's set.

## 5. Accumulated-context window size — ruled out, not a cost

`llm_judge_relevance()` caps the "already gathered" context it shows the
model at the last 30 items (`accumulated[-30:]`, `app/retrieval/
traversal.py`). Tested 0, 10, and 30 accumulated items in the prompt,
same candidates each time: **6.29s, 5.89s, 5.02s** — no meaningful
difference, within call-to-call noise. This is not where the time goes;
not worth trimming further.

## 6. Alternate `ANSWER_ENGINE` models — one lead, unverified

A quick single-item strict-JSON-schema test (not the full multi-candidate
reliability check every other model swap got today — see caveat below):

| Model | Result |
|---|---|
| `Qwen/Qwen3-30B-A3B-Instruct-2507` (current) | 0.56s avg, reliable |
| `google/gemma-3-27b-it` | **0.23s avg**, reliable on this test |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | FAIL — empty content |
| `zai-org/GLM-5.3-Flash` | FAIL — malformed JSON |

The two failures are the same class of bug as the morning's
`RETRIEVAL_MODEL` incident (a model that doesn't reliably honor strict
JSON schema output) — ruled out. `google/gemma-3-27b-it` looks
promising (roughly 2x faster than the current model on this trivial
test) but **this alone isn't enough to switch on** — it was one
single-boolean judgment, not the 5-candidate batched judgments a real
hop sends, and not run enough times to rule out the same intermittent-
failure risk `RETRIEVAL_MODEL`'s first replacement candidate turned out
to have. Worth the same treatment every other model decision got today
(multiple runs, realistic candidate batch size, live traversal test)
before adopting — not done here, this audit ran out of scope for it.

## Recommendation

The candidate-cap fix already shipped today is the real win; nothing
found here comes close to it. If more speed is wanted next:

1. **Test `google/gemma-3-27b-it` properly** (multi-candidate batches,
   several runs, a live traversal) as a faster `ANSWER_ENGINE` — the
   only lead here with real upside, if it holds up under the same
   scrutiny `RETRIEVAL_MODEL`/`REASONER_MODEL` got today.
2. **Investigate `fetch_hop_neighbors`'s ~1.3s/hop** — a real, small,
   unexplained fixed cost, worth a Cypher `EXPLAIN`/`PROFILE` pass.

Everything else tested here (skipping query formation, `top_k` tuning,
`max_depth` tuning below its current effective ceiling, trimming the
context window) either costs real accuracy, has no reliable direction,
or isn't where the time goes. None implemented — left as a decision for
whoever picks this up next.
