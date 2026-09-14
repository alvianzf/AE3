# v6.2 — Retrieval latency follow-up audit

**Status: investigated, not implemented.** A new version folder rather
than appending to `v6.1/` (ingestion latency) — same day, same class of
question, but a different pipeline stage with its own numbers and its
own (largely negative) findings. Per [`specs/README.md`](../README.md)'s
own rule, `v6.1/` is a released folder and isn't edited after the fact.

**Trigger**: the same day's `TRAVERSAL_MAX_CANDIDATES_PER_HOP` fix (20→5,
plus dropping the required `reason` field) cut a real seed+traversal call
from 94.64s to 9.93s. The user asked what else could push retrieval
speed further — this is that investigation.

- [**01 · Retrieval latency follow-up**](01-retrieval-latency-followup.md) —
  answer: not much is left on the table. Five candidate levers were
  tested live against production; four don't hold up (skipping the
  search-query-forming LLM call trades real accuracy for unreliable time
  savings; `TRAVERSAL_SEED_TOP_K` and `TRAVERSAL_MAX_DEPTH` have no
  consistent direction now that the candidate-cap fix already makes most
  traversals stop naturally well before max depth; the accumulated-
  context window size is noise, not a cost). One real fixed cost was
  found and left unfixed (`fetch_hop_neighbors`, ~1.3s/hop of Neo4j
  overhead, separate from the LLM call). One promising but unverified
  lever surfaced (`google/gemma-3-27b-it` as a faster `ANSWER_ENGINE`
  candidate — needs the same multi-candidate reliability check every
  other model swap got today before it's trustworthy).

## What this does not change

No code in `app/` was touched, no config changed. Timed investigation
only, against production's real Nebius credentials, real Neo4j data, and
three different real questions (not just the one question prior timing
work in this session used) — written up for whoever decides whether
squeezing more out of retrieval latency is worth the next round of
effort.
