# Model routing: a dedicated deployment, EU-west2, and two thinking-disable mechanisms

## Where things ended up

| Role | Model | Endpoint |
|---|---|---|
| Reader | `dedicated/Qwen/Qwen3-32B-Ckn0Os` | global |
| Graph-builder | `dedicated/Qwen/Qwen3-32B-Ckn0Os` | global |
| Checker-LLM | `dedicated/Qwen/Qwen3-32B-Ckn0Os` | global |
| Embedder | `dedicated/Qwen/Qwen3-Embedding-8B-R-HErT` | global |
| Reasoner | `moonshotai/Kimi-K3` | **eu-west2** |
| Answer Engine | `moonshotai/Kimi-K3` | **eu-west2** |

Three separate deployments now back six roles: a dedicated Qwen3-32B
endpoint the user provisioned, a dedicated Qwen3-Embedding-8B endpoint
(same), and Kimi-K3 — the only model Nebius serves out of EU-west2 at
all (confirmed via a direct `GET /v1/models` probe against that
region: one entry, full stop). None of the Qwen models exist there.

## Why Kimi-K3 isn't backing more roles

Kimi-K3 was tried for Reader/Answer-Engine/Checker-LLM too, thinking-
disabled the same way as the Reasoner. It works correctly (verified
live: valid strict-JSON output on every schema this app uses), but
paired live trials — identical prompts, both models, real traversal/
reasoner calls — showed Kimi-K3 consistently slower than Qwen3-235B,
every single trial, by 5-23 seconds depending on the call:

| Question | Kimi-K3 | Qwen3-235B | Gap |
|---|---|---|---|
| Metformin/PCOS (run 1) | 27.77s | 18.03s | +9.7s |
| Metformin/PCOS (run 2) | 25.88s | 3.03s | +22.9s |
| Vitamin D/sleep | 6.32s | 0.71s | +5.6s |

No trial where Kimi won. It remains the Reasoner/Answer-Engine choice
specifically *because* it's the only thing on EU-west2, not because
it's faster — a deliberate residency-vs-speed tradeoff, not an
oversight.

## Two real compatibility bugs, not just a config flip

**Two different thinking-disable mechanisms.** Kimi-K3 respects
`{"thinking": {"type": "disabled"}}`. The dedicated Qwen3-32B
deployment ignores that key entirely — it needs `{"chat_template_kwargs":
{"enable_thinking": false}}` instead, and defaults to thinking-on. A
suggested `reasoning_effort: "none"` top-level parameter was tested
live and confirmed **not** to work on this deployment either — the
`chat_template_kwargs` form is the one that actually does. Worse than
Kimi's version of this problem: this Qwen3 deployment inlines the
`<think>...</think>` block directly in the message content instead of
a separate `reasoning_tokens` usage field, which would have silently
broken `chat_json()`'s strict JSON parsing outright, not just added
latency, on every Reader/Graph-builder/Checker-LLM call.

Fixed by merging both keys into one shared `NO_THINKING` constant
(`app/clients/llm_client.py`) — confirmed live that each model family
ignores the other's key harmlessly, so no per-call-site branching on
model name is needed. `chat_json()` gained an `extra_body` parameter
(previously only `chat_text()` had one) so this could be wired into
Reader (`read_source`/`extract_article`), Graph-builder
(`extract_graph`/`suggest_entity_merges`), and Checker-LLM (`check`) —
none of which had ever needed thinking-disable before, since neither
had ever run a reasoning model.

**A much lower `max_tokens` ceiling.** `chat_json()`'s default
(100,000) exceeded the dedicated deployment's real limit — a hard
`BadRequestError` ("max_tokens cannot be greater than
max_model_len=40960"), not a truncation. Lowered the default to
20,000, still far above any real response shape this app's schemas
produce (verified: Reader 3.20s, Graph-builder 3.20s with correct
entities/relationships, entity-merge suggestion 1.02s, Checker-LLM
1.76s, all valid JSON, no `<think>` leakage).

## Verified live

Every role re-tested after each config change, both individually
(direct module calls against real Nebius/dedicated endpoints) and as a
full pipeline (a real `seed_search.seed()` → `GraphTraversalRetriever`
run completing correctly end to end against production Neo4j data,
confirmed at 4-5s total for seed search + a multi-hop traversal, both
under Kimi-K3/EU and under the dedicated Qwen3-32B deployment).

## What this does not change

The retrieval/reasoning logic itself is untouched — this is entirely
about which model a role's client points at and how its thinking gets
suppressed, not new business logic. `v6.3`'s LLM-as-judge Checker
design is unchanged; only the model backing `Role.CHECKER` moved (from
its original `Qwen3-30B-A3B-Instruct-2507` default, to Kimi-K3
briefly, to the dedicated Qwen3-32B deployment now).
