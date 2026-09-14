# v6.1 — Ingestion latency audit

**Status: investigated, not implemented.** A new version folder rather
than appending to `v6/` because `v6/` covers the Postgres migration —
this is an unrelated finding (ingestion pipeline performance), and per
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
  both confirmed non-reasoning). But two real, unrelated latency sources
  exist: the Graph-builder loop runs one sequential call per passage
  (O(chunks), ~26s for 10 passages, no concurrency), and the Embedder has
  a large fixed per-call latency (~9.5s for one text) not explained by
  reasoning tokens at all. Neither was fixed here — both are documented
  with concrete next steps, left as a product decision.

## What this does not change

No code in `app/` was touched. Nothing here is implemented — this is a
timed, live investigation against production's real Nebius credentials
and models, written up for whoever decides whether ingestion latency is
worth spending effort on next.
