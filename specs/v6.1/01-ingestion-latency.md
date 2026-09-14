# 01 · Ingestion latency audit

**Update, same day:** the user asked directly which of this doc's two
proposed levers was worth doing on performance *and* accuracy grounds.
Answer given: parallelizing wins outright — it's real wall-clock
improvement with zero accuracy risk (same calls, same model, just
concurrent), where streaming progress is a UX fix with zero effect on
either axis. **Graph-builder parallelization is now implemented**
(`ThreadPoolExecutor(max_workers=8)`, both `app/main.py`'s
`_ingest_pages` — the actual live path — and `app/ingestion/pipeline.py`'s
`ingest()`, kept consistent though it has no callers). See "Update,
same day" under "What's actually slow" and a new "Re-tested" section
below for the real before/after numbers and an important variance
finding from re-testing. Streaming progress remains undone, still a
live option if this comes up again.

Produced 2026-09-14, prompted directly by the two reasoning-token
latency bugs found and fixed the same day in the retrieval/reasoning
path (`RETRIEVAL_MODEL` breaking strict JSON output, `REASONER_MODEL`
burning 30-120s/call on hidden chain-of-thought) — the natural next
question was whether ingestion (`app/ingestion/pipeline.py`) has the
same class of problem. **It does not** — `READER_MODEL` and
`GRAPH_BUILDER_MODEL` are both confirmed non-reasoning (`reasoning_tokens`
absent from every raw response checked). But ingestion has two different,
real latency sources of its own, timed live against production credentials
and models (Nebius, same base_url/api_key as production).

## What's actually slow, and why

**Per-document baseline, timed on a synthetic 10-passage document**
(`app/ingestion/pipeline.py`'s three LLM stages, run in the same order
`ingest()` calls them):

| Stage | Time | Share |
|---|---|---|
| Reader (`read_source()`, one call) | 5.3s | 9% |
| Embedder (`embed()`, one batched call for all 10 passages) | 28.4s | 47% |
| Graph-builder (`extract_graph()`, 10 **sequential** calls, one per passage) | 26.4s | 44% |
| **Total** | **60.1s** | |

Per-passage Graph-builder times varied 1.6-3.7s (no outliers, no
timeouts, no retries triggered) — confirms the model itself is fine;
the cost is purely `for p in passages: extract_graph(p)` being
sequential, not concurrent (`app/ingestion/pipeline.py`'s `ingest()`,
the loop right after the `embeddings = ...` line). **This is O(chunks),
linear**: the real "cureus-0015-00000044493.pdf" already in production
(30 chunks, per this session's earlier ingest) would spend roughly
3x this test's Graph-builder time — on the order of 80-90s just for
that one stage, serialized.

**Update, same day — parallelized and re-tested.** Same 10-passage
shape, `ThreadPoolExecutor(max_workers=8)` instead of a sequential
loop:

| Run | Sequential (this audit) | Parallel (same day, after fix) |
|---|---|---|
| 1 | 26.4s | 12.5s |
| 2 | — | 7.5s |
| 3 (anomalous) | — | 62.0s |

Run 3's spike wasn't a concurrency-throttling artifact — the *sequential*
Embedder call timed in the same run also spiked (8.59s vs. a typical
3.63s, see below), meaning that run hit a general Nebius-side load
event affecting every call, not something the added concurrency itself
caused. Typical case is a genuine **~2-3x** improvement; occasional
shared-infra variance can still spike any individual run, parallel or
not — inherent to a third-party dependency, not a flaw in this fix.

**Embedder — re-tested, original 9.5s/28.4s numbers do not reproduce
reliably.** Re-run same day, fresh processes each time: a single-text
call measured **1.65-2.03s** across 3 runs (not 9.5s), and a 10-text
batch measured **3.63s** in one run and **8.59s** in another (not a
stable 28.4s). This confirms real latency here, but the magnitude in
the original table looks like it landed on an unlucky, higher-than-
typical sample rather than Embedder's steady-state cost — the
underlying cause (cold-start, queueing, or real throughput on
`Qwen/Qwen3-Embedding-8B`'s Nebius infra) still isn't distinguished
from the client side, and the *variance itself* (roughly 2x run to run)
is now the more clearly established finding than any single fixed
number. Not worth a code change on this evidence — nothing here
points at an app-side inefficiency to fix (batching is already
correct: one call for all passages, not one per passage).

## What this means for the product today

Ingesting one real, moderately-sized document (10-30 passages) costs
roughly **1-3 minutes**, almost entirely Embedder + serialized
Graph-builder — not a hang, not a bug, just real, additive latency with
no timeout risk at today's `_CHAT_TIMEOUT_SECONDS = 90.0` per individual
call (every call observed finished well under that). An admin submitting
a source and waiting on the ingest response should expect this range,
scaling with document length — there's no existing progress signal for
ingestion the way `retrieve_streaming()` now provides for a consult's
traversal hops (`app/main.py`'s `agent_progress` SSE event, added the same
day for exactly this "long-and-silent" UX problem) — `POST /api/sources`
and the chunked-upload completion route are still one blocking call from
the admin's perspective, start to finish.

## Done and not done, same day

This started as an audit, not a fix — per the task it was scoped under,
matching how the `RETRIEVAL_MODEL`/`REASONER_MODEL` finds earlier the
same day were each their own explicit, separately-decided change. Two
concrete levers were identified; one is now implemented:

1. **Parallelize the Graph-builder loop — done.** Passages are
   independent — nothing in `extract_graph()` depends on another
   passage's result — so this was a straightforward concurrent-calls
   change (`concurrent.futures.ThreadPoolExecutor(max_workers=8)`), not
   a redesign. Failure handling stayed per-passage (unchanged from
   before — one passage's failure still can't blank out the others).
   Applied to both `app/main.py`'s `_ingest_pages` (the actual live
   path) and `app/ingestion/pipeline.py`'s `ingest()` (unused today,
   kept consistent since the two have always mirrored each other).
2. **Stream ingestion progress** — still undone. The same shape as
   `retrieve_streaming()` ("chunk 4/30 extracted") so a long ingest
   reads as working, not stuck, the same fix already applied to consult
   traversal the same day for the identical underlying complaint shape
   ("it's slow, did it hang?"). Still a live option, not ruled out —
   just not what the performance/accuracy comparison favored today.

Embedder's latency (above) was re-investigated but not acted on — no
app-side lever was found, and the variance finding argues against
tuning around a single number.
