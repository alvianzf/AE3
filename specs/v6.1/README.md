# v6.1 — Ingestion latency audit

**Status: partially implemented.** Started as an investigation; the
Graph-builder parallelization it proposed was implemented the same day
after the user compared the two proposed levers on performance and
accuracy grounds. A new version folder rather than appending to `v6/`
because `v6/` covers the Postgres migration — this is an unrelated
finding (ingestion pipeline performance), and per
[`specs/README.md`](../README.md)'s own rule, released version folders
aren't edited after the fact regardless of topic overlap.

**Trigger**: two reasoning-token latency bugs were found and fixed live
in production the same day (2026-09-11 → 2026-09-14 session) —
`RETRIEVAL_MODEL` and `REASONER_MODEL` were both silently reasoning
("thinking") models burning 30-120s+ per call on hidden chain-of-thought
before producing output. The natural next question: does
`app/ingestion/pipeline.py` (Reader + Embedder + Graph-builder, the
other three AI-team roles making real Nebius calls) have the same
problem?

- [**01 · Ingestion latency audit**](01-ingestion-latency.md) — answer:
  no reasoning-token bug in ingestion (`READER_MODEL`/`GRAPH_BUILDER_MODEL`
  both confirmed non-reasoning). Two real, unrelated latency sources were
  found: the Graph-builder loop ran one sequential call per passage
  (O(chunks), ~26s for 10 passages, no concurrency) — **now parallelized,
  ~2-3x faster, implemented same day** — and the Embedder has a large
  per-call latency that turned out to be highly variable on re-test
  (1.65-8.59s across runs, not the ~9.5s/28.4s the original audit found),
  with no app-side lever identified. Streaming ingest progress (the
  second originally-proposed lever) remains undone — not ruled out, just
  not what the performance/accuracy comparison favored.

## What this does not change

The Graph-builder parallelization touches `app/main.py`'s `_ingest_pages`
(the actual live ingest path) and `app/ingestion/pipeline.py`'s `ingest()`
(kept consistent, though it has no callers). Nothing else in `app/`
changed — no streaming progress, no Embedder-side fix, no schema or API
changes. This remains a live, timed investigation against production's
real Nebius credentials and models first, with one of its two findings
acted on the same day — not a fully closed-out spec.
