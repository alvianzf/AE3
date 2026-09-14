# 01 · Ingestion latency audit

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

**Embedder is the single biggest cost, and it isn't chunk-count-driven
the way Graph-builder is** — a lone-text `embed()` call took **9.5s**,
and a 10-text batched call took **28.4s** (not 10x — there's real batching
efficiency, but a large fixed-per-call latency dominates either way).
This is `Qwen/Qwen3-Embedding-8B` on Nebius's infra; not a reasoning-token
issue (embeddings don't have that field at all), and not something this
audit found a lever for the way `chat_text`'s new `extra_body` passthrough
(commit found in `app/clients/llm_client.py` as of this audit, same day)
gives the Reasoner. Whether it's a cold-start cost per call, a queueing
effect, or genuinely the model's real throughput on this infra wasn't
distinguished here — worth a follow-up if ingestion latency becomes a
product priority, but out of scope for what this audit could establish
from the client side alone.

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

## Not done here, deliberately

This is an audit, not a fix — per the task this was scoped under,
matching how today's earlier `RETRIEVAL_MODEL`/`REASONER_MODEL` finds
were each their own explicit, separately-decided change. Two concrete
levers exist if ingestion latency becomes worth spending effort on:

1. **Parallelize the Graph-builder loop.** Passages are independent —
   nothing in `extract_graph()` depends on another passage's result — so
   this is a straightforward concurrent-calls change (e.g.
   `concurrent.futures.ThreadPoolExecutor`), not a redesign. Failure
   handling would need to stay per-passage (already true today, per
   `ingest()`'s own comment on why the try/except is inside the loop).
2. **Stream ingestion progress**, the same shape as `retrieve_streaming()`
   — "chunk 4/30 extracted" — so a long ingest reads as working, not
   stuck, the same fix already applied to consult traversal today for
   the identical underlying complaint shape ("it's slow, did it hang?").

Neither was implemented or decided here — both are product/effort calls,
consistent with how every model/latency change today was made with the
user, not silently.
