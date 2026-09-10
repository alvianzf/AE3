# 01 · Provider swap: Anthropic → Nebius, and the new five-model role split

**Status: spec only.** No code changed. `NEBIUS_API_KEY` /
`NEBIUS_BASE_URL` were added to local `.env` and `.env.example` as prep,
not read by any code path yet.

## The mapping, as given, with the job description for each

The role list was given twice — a short label pass, then a corrected pass
with a one-line job description per role. The job descriptions are the
source of truth below; **the roles don't map 1:1 onto the current
Reader/Librarian/Answer/Checker names the way the labels alone suggested**
— see [§Why this isn't a simple rename](#why-this-isnt-a-simple-rename-of-the-existing-four-roles).

| Role (as given) | Model | Job (as given) | Closest current equivalent |
|---|---|---|---|
| Reading a new source | **Qwen3.6-27B** | Summarises, tags the topics, drafts source cards | `READER_MODEL` (`read_source()`, `app/llm.py:129`) — matches directly |
| Build the RAG Graph | **MedGemma-27B** | Pulls out medical concepts and how they connect | The concept-extraction sub-call inside `read_source()` (currently `cfg.reader_model`, `app/llm.py:205`) **and** the graph-merge step (currently `cfg.librarian_model`, `app/llm.py:267`) — see below |
| Embedder | **Qwen3-Embedding-8B** | Embeds KB chunks into the database | No current equivalent — genuinely new. Retrieval today is explicitly non-embedding (`.env.example`: *"Retrieval — the librarian picks from source cards; no embeddings"*) |
| Answer Engine | **Qwen3 8B** | Works out what's being asked and what to go fetch | `LIBRARIAN_MODEL`'s query-time job (`app/llm.py:409`, docstring: *"turns a question into what to look for; it does not answer"*) |
| Reasoner (Specialist) | **KIMI K3** | Senior reasoner — reads retrieved KB + patient data, reasons over it | `ANSWER_MODEL` (`app/llm.py:444` `answer()`, docstring names this role "Specialist" too — genuine naming agreement, not a coincidence worth second-guessing) |
| Checker | **Qwen3.6-27B** (same model as Reader, different system prompt/role) | *(not separately described — added after the initial four-role pass, confirmed as a distinct role reusing the Reader model)* | `CHECKER_MODEL` (`app/llm.py:541` `check()`) — matches directly |

## Why this isn't a simple rename of the existing four roles

The current pipeline has **four** model slots (`READER_MODEL`,
`LIBRARIAN_MODEL`, `ANSWER_MODEL`, `CHECKER_MODEL`) but `LIBRARIAN_MODEL`
actually does two different jobs at two different times, both named
"Librarian" only because they happened to share a model:

1. **Ingestion-time**: merging extracted concepts into the graph
   (`app/llm.py:267`, `MERGE_SYSTEM`).
2. **Query-time**: reading a practitioner's question and deciding what to
   retrieve (`app/llm.py:409`, the docstring's "turns a question into what
   to look for").

The new role list **splits these into two named, separately-modeled
roles** — "Build the RAG Graph" (MedGemma-27B, ingestion-time, and per its
job description it also absorbs the concept-*extraction* sub-call that
currently runs on `READER_MODEL` at `app/llm.py:205`) and "Answer Engine"
(Qwen3 8B, query-time). **"Answer Engine" is a confusing name for this
role** — it does not write the answer; per its own job description
("works out what's being asked and what to go fetch") it's the retrieval
planner, i.e. today's query-time Librarian. The role that actually writes
the answer is "Reasoner (Specialist)" (KIMI K3) — confirmed independently
by both its job description ("reads retrieved info + patient data,
reasons based on it") and by the fact that the current codebase's own
docstring already calls that exact role "Specialist"
(`app/llm.py:5`). Whoever implements this should **not** wire "Answer
Engine" → `answer()` just because of the name; wire it to the retrieval/
planning step, and "Reasoner (Specialist)" → `answer()`.

## What changes mechanically in `app/llm.py`

- **Client**: `anthropic.Anthropic()` → an OpenAI-compatible client
  (`from openai import OpenAI; OpenAI(base_url=NEBIUS_BASE_URL,
  api_key=NEBIUS_API_KEY)`), per the example call provided. `client_for()`
  changes from taking an Anthropic key to whatever the resolved
  BYO-key story ends up being — see
  [§Open question: the practitioner-owned key](#open-question-the-practitioner-owned-key)
  below.
- **New dependency**: the `openai` Python package, alongside — not
  necessarily instead of — `anthropic`, per [CLAUDE.md](/Users/azfaturrahman/.claude/CLAUDE.md)'s
  "say why, so the choice is visible" rule: it's the only way to speak the
  OpenAI-compatible protocol Nebius exposes.
- **`_json_call()` (`app/llm.py:29-48`) needs a real rewrite, not a
  find-replace.** It currently uses Anthropic's `output_config: {format:
  {type: "json_schema", schema}}` and reads `response.content` (a list of
  typed blocks, filtered for `type == "text"`). OpenAI's structured-output
  shape is different: `response_format: {"type": "json_schema",
  "json_schema": {"name": ..., "schema": schema, "strict": true}}`, and
  the result lives at `response.choices[0].message.content` (a plain
  string) — not a drop-in parameter rename, a different response object
  shape to parse.
- **`_usage_of()` (`app/llm.py:22-25`)** reads
  `response.usage.input_tokens` / `output_tokens` (Anthropic's field
  names). OpenAI's shape is `response.usage.prompt_tokens` /
  `completion_tokens` — needs updating or every usage-tracking call site
  silently breaks (`KeyError`/`AttributeError`, not a wrong-but-plausible
  number, so this should fail loud in testing rather than ship silently
  wrong).
- **`ping()` (`app/llm.py:53-56`)** calls `_client.models.retrieve(...)` —
  confirm the OpenAI SDK's equivalent (`client.models.retrieve(model_id)`
  exists on OpenAI-compatible APIs generally, but Nebius's actual support
  for that specific call needs a real check against their API, not an
  assumption from the SDK shape alone).
- **Model ID strings**: "Qwen3.6-27B", "MedGemma-27B", etc. are the
  human-readable names given in this conversation, not necessarily the
  exact `model=` string Nebius's API expects (their catalog IDs are
  typically namespaced, e.g. `Qwen/Qwen3-32B`-style). **Confirm the exact
  catalog ID for each of the six model slots against Nebius's own model
  list before wiring `READER_MODEL` etc.** — using the human label
  verbatim as the API's `model` parameter is a real, first-try failure
  mode here, not a hypothetical one.
- **Six config vars, not four**: `READER_MODEL`, `GRAPH_BUILDER_MODEL`
  (new — was folded into `LIBRARIAN_MODEL`), `EMBEDDER_MODEL` (new),
  `RETRIEVAL_MODEL` (new name suggested for the renamed query-time
  "Answer Engine" role, to avoid the misleading "answer" in its name —
  naming is implementer's call, flagged here only so "Answer Engine"
  isn't wired to the wrong function per the naming trap above),
  `REASONER_MODEL` (was `ANSWER_MODEL`), `CHECKER_MODEL` (unchanged
  role, new model).

## Open question: the practitioner-owned key

Today, each practitioner sets their **own** Anthropic API key
(`core_store`'s `anthropic_api_key_encrypted`, surfaced in
`profile/+page.svelte` and gating Consult per
`(practitioner)/practitioner/+layout.svelte:6-9`) — Reasoner/Answer and
Checker calls at query time run against *that* practitioner's key, while
ingestion (Reader, graph-building) runs against the app's own
server-side key. **Switching the provider doesn't by itself resolve
whether that BYO-key model continues**: does each practitioner now bring
their own Nebius key (rename the field, the onboarding step, and
[v4.1/03 CR2](../v4.1/03-known-issues-and-gaps.md#cr2--the-practitioner-onboarding-checklist-can-never-show-not-done)'s
just-fixed checklist copy), or does the app move to one shared
server-side Nebius key for every practitioner (a real pricing/billing
model change, since practitioner-paid API usage was presumably the reason
for BYO-key in the first place)? **Not decided here** — needs a product
call before implementation, since it changes onboarding UI, the
`profile` endpoint's shape, and possibly billing.

## Open question: what consumes the Embedder's output

"Embeds KB chunks into the database" is confirmed as *additive* — the
existing graph/source-card retrieval stays the primary path (explicitly
confirmed, not being replaced). That leaves genuinely open: **which
database** (Neo4j supports vector indexes natively — likely the natural
fit, since the graph already lives there — or a separate vector store),
and **what feature actually reads these embeddings** once written (a
semantic-search fallback when the graph retrieval comes up short? Source
deduplication at ingest time? Something else?). Implementing the write
path without a defined read path produces a real cost (compute + storage
for every ingested chunk) with no product feature behind it yet — worth
pinning down the consuming use case before building the write side, not
after.
