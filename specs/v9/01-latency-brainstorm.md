# v9/01 — Backend pipeline latency: candidates and recommendation

## The brief

"I want the backend process to be as accurate if not more than current
one, but with less resource needed and higher speed at least 30%
faster. I need the same API contract as current so that we don't have
to adjust the FE much. But if we dont have another choice, you can
alter the FE contract or logic." Followed by: "You can change the
backend logic, framework, logic, and even tools and libraries (like
redis etc) to fit the goal. But it needs to be free."

So the bar is: **≥30% faster wall-clock**, **same-or-better accuracy**,
**free tools/libraries only**, **same API contract unless there's
genuinely no other way**. "Find one that's best," not build several —
this spec evaluates candidates and recommends one package, rather than
shipping a menu of options for later.

## Method

Read the real pipeline end to end before proposing anything —
`app/ingestion/pipeline.py`, `app/ingestion/queue.py`,
`app/retrieval/{seed_search,traversal,general_lookup,pgvector_store}.py`,
`app/graph/store.py`'s hot-path queries, `app/patient/context.py`,
`app/reasoning/{reasoner,llm_checker}.py`, `app/clients/{llm_client,
anthropic_client}.py`, `app/config.py`, and the consult endpoint
(`app/main.py`'s `/api/me/consult`) — not assumed from memory, and not
re-litigating what the v6.1/v6.2/v6.3 latency specs already tried
(sequential graph-builder extraction parallelized; seed-query-forming
call confirmed worth its cost; `TRAVERSAL_MAX_CANDIDATES_PER_HOP`
20→5; the local HHEM checker replaced by an LLM-judge checker). This
spec only proposes what's genuinely new.

**A live fact that changes the shape of this problem**: `curl
.../api/health` against production right now shows `reader` and
`graph_builder` resolving to `claude-sonnet-5`/`claude-haiku-4-5` —
**production is currently running the Anthropic provider**, not the
Nebius default `config.py` documents, and `embedder` resolves to
`sentence-transformers/all-MiniLM-L6-v2` at `ping_ms: 0.0` — **the
"emergency-only" local-embedder override (`EMBEDDER_FORCE_LOCAL`) is
also currently live**, per `config.py`'s own comment, because Nebius's
account ran out of budget on 2026-11-02. Two decisions this spec would
otherwise have had to propose from scratch are already true in
production today, just not as deliberate, permanent choices.

## Pipeline map (what's actually sequential vs. already parallel)

**Ingest** (`ingestion/pipeline.py:ingest()`):
1. `store.content_hash()` + `store.find_by_hash()` — 1 Neo4j round trip, idempotency gate, before any LLM call. [sequential, cheap]
2. `read_source()` — 1 Reader LLM call (title/summary/grade/folder). [sequential]
3. `store.chunk_pages()` — pure Python, no network. [sequential, free]
4. `get_client(Role.EMBEDDER).embed(...)` — 1 batched embedding call for every chunk. [sequential]
5. `extract_graph()` per passage — already parallelized, `ThreadPoolExecutor(max_workers=8)` (v6.1). [parallel]
6. `store.ingest_document()` — 1 Neo4j write transaction. [sequential]

**The one real new finding here**: step 2 (Reader) and steps 3–4
(chunk + embed) are **fully independent** — `read_source()`'s result
(`card`) is only consumed at step 6, nowhere in between. Today they
still run strictly in series (2, then 3, then 4) for no reason visible
in the code or any prior spec — nothing stops the Reader call from
running concurrently with chunking+embedding.

**Consult** (`/api/me/consult`, deep-research mode):
1. `get_patient_context()` — 1 vault lookup (SQLite/Postgres), cheap. [sequential]
2. `seed_search.seed()` — 1 LLM call (form the search query) + 1 embed call + 2 Neo4j index queries (vector, fulltext) + 1 more Neo4j query (`entities_mentioned_by_chunks`). [sequential — each step's input depends on the previous]
3. `GraphTraversalRetriever.retrieve_streaming()` — up to `traversal_max_depth` (5) hops, **each** hop: 1 Cypher query (`fetch_hop_neighbors`, already a single round trip, not N+1) + 1 batched LLM relevance-judgment call. [hops are forced-sequential by the algorithm itself — hop N+1's frontier is literally hop N's judged-relevant output]
4. `reasoner.answer()` — 1 LLM call. [sequential, depends on 3]
5. `llm_checker.check()` — 1 LLM call. [sequential, depends on 4]
6. (conditional) one retry: steps 4+5 again, only if step 5 says "weak". [sequential, rare path]

Worst case: **2 (seed) + 5 (hops) + 1 (reasoner) + 1 (checker) + 2
(retry) = up to 11 sequential LLM round trips** for one consult. No
N+1 query pattern anywhere in the hot path — every Neo4j query already
batches its candidate set into one round trip (`fetch_hop_neighbors`,
`seed_chunks_by_vector/fulltext`, `entities_mentioned_by_chunks`).
`general_lookup` mode is already the fast path (1 embed + 1 pgvector
query, no traversal) and isn't a target here.

## Candidates considered

| # | Candidate | Free? | API contract | Accuracy risk | Verdict |
|---|---|---|---|---|---|
| A | Anthropic prompt caching (`cache_control` on every role's static system prompt) | Yes — Anthropic's own feature, cached reads are *cheaper* than full reprocessing, not an add-on cost | None — internal to `anthropic_client.py` | None — same prompt, same model, same output | **Recommended** |
| B | Run the ingest Reader call concurrently with chunk+embed | Yes — just reordering existing calls | None | None — same calls, same results, just reordered | **Recommended** |
| C | Formalize the local embedder as the deliberate default, not an undocumented emergency fallback | Yes — `sentence-transformers` already vendored, zero marginal cost, zero network hop per call | None for `/api/me/consult` itself; **does** require re-embedding the existing corpus at the local model's dimension (already true in production right now) | Needs a real before/after retrieval-quality check (see below) — this is the one candidate that isn't risk-free by inspection alone | **Recommended, conditional on the quality check passing** |
| D | A Redis-backed response/embedding cache for repeated (practitioner, client, question) consults | Yes — Redis OSS is free | None | None | Considered, not recommended as a centerpiece — see below |
| E | Swap to a different, unverified "faster" model for Reasoner/Answer-engine | Possibly, if already-available in the same catalog | None | Unknown until measured | Not recommended now — needs live A/B first, not assumed |
| F | Raise `ingestion_concurrency` above 1 | Yes | None | None for single-ingest latency; this is a throughput lever, not a per-request latency one | Out of scope for this spec's "faster per request" goal; noted as a separate, smaller follow-up |

### Why D (Redis) is not the centerpiece

A practitioner's real consult questions are open-ended clinical
questions about a specific patient at a specific point in that
patient's care — the exact (question, patient, library-state) tuple
repeating verbatim is the uncommon case, not the common one, and the
knowledge library itself changes over time (new ingests), so a cached
traversal result can silently go stale the moment a new source lands.
A cache here would mostly cache misses, for real staleness risk, to
speed up a rare case. Rejected as the primary lever; worth revisiting
only if live traffic data later shows real repeat-question volume —
not assumed here.

### Why E (model swap) is not recommended yet

Every prior latency spec in this project (v6.1-v6.3) that touched
model choice did so by running real paired trials against production,
not by reasoning about a model from its name or benchmark reputation —
and more than once a model that looked faster on paper (MiniCheck,
Kimi-K3 with thinking disabled) came back *slower* in a real trial.
Recommending a specific swap here without doing that same live
measurement would be exactly the kind of guess this project's own
track record argues against. If the recommended package (A+B+C)
doesn't reach the 30% bar on its own, a model trial is the natural next
investigation — not proposed as fact here.

## Recommended package: A + B + C

### A — Anthropic prompt caching

`anthropic_client.py`'s `chat_json`/`chat_text` send the full system
prompt as plain text on every call. Every hot-path system prompt is
static and reused across many calls: `RELEVANCE_SYSTEM` (traversal,
once per hop, every consult), `CHECK_SYSTEM` (once per consult),
`REASONER_SYSTEM` (once per consult, twice on a retry), `KG_BUILDER_
SYSTEM`/`READER_SYSTEM` (every ingest). Marking the system block (and,
where a prompt has one, the static library-wide context like
`known_topics`/`known_folders`) with `cache_control: {"type":
"ephemeral"}` lets Anthropic skip reprocessing those tokens on every
repeat call within the cache TTL — a cached read is both measurably
faster (no reprocessing of the cached prefix) and cheaper than a full
read, per Anthropic's own documented behavior. Zero new dependency,
zero API-contract change (purely inside `AnthropicLLMClient`), zero
accuracy change (identical prompt, identical model).

Only applies while the superadmin provider toggle is set to
`anthropic` — which, per the live health check above, is the
production default right now. If a future deploy flips back to Nebius,
this lever goes inactive for that provider (Nebius's token-factory API
surface doesn't expose the same `cache_control` mechanism this app has
confirmed); worth a parallel note in that client, not a blocker here.

### B — Parallelize the ingest Reader call

`ingestion/pipeline.py:ingest()` reorders to:

```
with ThreadPoolExecutor(max_workers=2) as pool:
    card_future = pool.submit(read_source, text, filename, kind, origin,
                              facets["topics"], facets["folders"])
    passages = store.chunk_pages(pages or [(None, text)])
    embeddings = get_client(Role.EMBEDDER).embed([p["text"] for p in passages])
    card = card_future.result()
```

Same calls, same results, same `store.ingest_document()` call at the
end — only the order changes. Saves the full wall-clock cost of the
Reader call on every ingest (it currently blocks chunking+embedding
for no reason), on top of whatever (A) saves on that same call's own
processing time.

### C — Local embedder as the deliberate default

Confirmed already live in production (forced by a billing outage, not
a deliberate choice) and reported `ok` by the health check. Formalizing
it means: flip `EMBEDDER_FORCE_LOCAL`'s default to `true` in
`config.py` (keep the env var as an override, don't remove the
knob — a future Nebius-embedding deployment is still a legitimate
choice for someone who wants it), update `embedding_dimensions`'
documented default to match `LocalEmbedderClient`'s real output size
instead of the Nebius Qwen3-Embedding-8B figure, and remove "emergency-
only" framing from the comments since this becomes the normal path.
Saves one full network round trip (Nebius) per embedding call —
`seed_search.seed()` and `general_lookup.lookup()` both make exactly
one — on every single consult and every ingest, replaced by in-process
CPU inference with zero per-call network latency and zero marginal
cost.

**The one real risk**: `all-MiniLM-L6-v2` is a materially smaller,
lower-capacity embedding model than `Qwen3-Embedding-8B` — retrieval
*quality* (not just speed) could regress if the smaller model's
vector-similarity seeding genuinely misses passages the larger model
would have surfaced. This is exactly the kind of claim this project's
own standing norm says must be measured, not assumed — see "Acceptance
bar" below. If the quality check fails, (C) is the one part of this
package to drop; (A) and (B) stand on their own regardless.

## What this does not touch

- No change to `traversal_max_depth`/`traversal_max_candidates_per_hop`
  — already tuned against real data in v6.2; re-litigating those
  without new evidence would be guessing, not grounded design.
- No change to which model each role uses — see "Why E is not
  recommended yet" above.
- No change to the Checker's algorithm, the traversal's stopping logic,
  or the Reasoner's prompt/rules — this is a latency spec, not a
  behavior spec; the practitioner-facing answer should come out
  byte-for-byte unchanged on the same inputs.
- No new paid dependency, no Redis, no new infrastructure to run or
  pay for.

## Acceptance bar — a live measurement, not an estimate

`/api/me/consult`'s response already carries `step_times` and
`total_time_s` per real call (added for the SSE progress stream) — the
exact instrumentation needed to verify this honestly already exists
for consult. Ingest has no equivalent per-stage timing today; adding
one (wrapping steps 2/3/4 in `ingest()` with `time.monotonic()`, logged
or returned the same way consult already does) is a small, necessary
part of implementing this, not optional — the 30% target cannot be
honestly claimed met without a real before/after number from this
app's own production shape, the same discipline v6.1/v6.2/v6.3 already
hold: a real timed trial against real documents/questions, both before
and after, not a reasoned-sounding estimate.

## Implementation, when approved

Not phased here (the request was for the brainstorm/recommendation,
not a build) — but worth naming the order this repo's own discipline
would use once this is approved: (1) add the missing ingest-stage
timing first, so there's a real "before" number to compare against;
(2) ship A and B together (independent of each other, both risk-free);
(3) measure; (4) evaluate C's retrieval-quality question specifically
(a side-by-side seed-search comparison, same question set, local vs.
Nebius embedding, judged for recall against a held-out relevant-
passage set) before flipping its default, since it's the one candidate
here that isn't free of accuracy risk by inspection alone.
