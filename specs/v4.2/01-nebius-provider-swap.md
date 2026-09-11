# 01 · Provider swap: Anthropic → Nebius, and the new five-model role split

**Status: implemented, not live-verified.** All three open items from the
first draft — the Checker's integration shape, the practitioner-owned-key
model, and the Embedder's consumer — are decided (see their sections
below) and the decisions are reflected in code (`app/llm.py`,
`app/config.py`, `app/main.py`, `app/knowledge.py`, `app/core_store.py`,
and the practitioner profile/dashboard frontend). **Code-confirmed only,
same caveat as [v4/04](../v4/04-known-issues.md)**: `npm run check` and
`npm run build` pass, and every backend module imports cleanly, but
nothing here has run against a real Nebius endpoint, a real Neo4j vector
index, or a downloaded HHEM-2.1-Open model — that live spot-check is
real, necessary follow-up work, not a formality.

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
| Checker (Anti-Hallucination) | **HHEM-2.1-Open** | Verifies every sentence against the sources it came from | `CHECKER_MODEL` (`app/llm.py:541` `check()`) — same *role*, resolved to a **direct classifier call, not an LLM chat completion** — see [§The Checker is a direct classifier call, not a chat completion](#the-checker-is-a-direct-classifier-call-not-a-chat-completion) below |

**Corrections, superseding earlier passes in this doc's drafting**: the
Checker was first given as "Qwen3.6-27B, same model as Reader" (wrong),
then as an unresolved choice between HHEM-2.1-Open and LettuceDetect. Both
superseded by the row above: **decided as HHEM-2.1-Open, called directly
as a classifier — no chat/completion model involved in checking at all.**

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

## The Checker is a direct classifier call, not a chat completion

**Decided**: no LLM is involved in checking at all. HHEM-2.1-Open is a
hallucination-detection / NLI (natural-language-inference) classifier,
not a chat model — it takes a (claim, evidence) pair and returns a
hallucination-probability score, with no system prompt, no JSON-schema
completion, none of `_json_call()`'s machinery. Concretely, this means:

- **`check()` (`app/llm.py:541-565`) is rewritten to call HHEM directly**,
  not through `_json_call()` or any OpenAI-style `/chat/completions`
  request — a separate, much simpler call path: `model.predict([(claim,
  evidence), ...])` or equivalent for whichever runtime hosts it (see
  next point), returning per-pair scores rather than a parsed JSON object.
- **Hosting**: HHEM-2.1-Open is a small (~600M-parameter) open-weight
  model, normally run via a `sentence-transformers`/`transformers`
  cross-encoder pipeline (CPU-viable, no GPU-inference API required) or
  self-hosted — **not necessarily served through Nebius's token-factory
  chat endpoint at all**. Confirm whether Nebius's catalog serves it
  behind an inference API, or whether it's simpler to load it directly in
  `app/llm.py` via `sentence-transformers` (a new dependency either way,
  but a much lighter one than routing through a hosted chat API for every
  check).
- **Per-sentence, not one holistic call**: today's `check()` asks a chat
  model "does this answer's claims hold up against these sources" as one
  JSON-schema call covering the whole answer. HHEM runs per (claim,
  evidence) pair, so the rewrite naturally becomes: split the drafted
  answer into sentences/claims, score each against its cited passage(s),
  and flag the answer (same downstream behavior as today —
  `vault.session_has_flagged_turn`, `app/main.py:1624-1628`) if any pair
  scores below a threshold. **A real function rewrite, confirmed, not a
  model-string swap** — flagged in the previous draft as a possibility,
  now confirmed as the actual shape.
- The **threshold for "flagged"** (what HHEM score counts as a likely
  hallucination) isn't set here — a calibration decision for whoever
  implements this, ideally validated against a few known-good/known-bad
  examples before shipping, not picked arbitrarily.

## What changes mechanically in `app/llm.py`

- **Client**: `anthropic.Anthropic()` → an OpenAI-compatible client
  (`from openai import OpenAI; OpenAI(base_url=NEBIUS_BASE_URL,
  api_key=NEBIUS_API_KEY)`), per the example call provided, constructed
  once at module level exactly like today's `_client` — no per-caller key
  anymore, see
  [§Decided: one shared server-side key](#decided-one-shared-server-side-key-byo-key-model-dropped-entirely)
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
  `REASONER_MODEL` (was `ANSWER_MODEL`), `CHECKER_MODEL` (unchanged role,
  now names a classifier, not a chat model — see previous section).

## Decided: one shared server-side key, BYO-key model dropped entirely

**Decided**: every practitioner now runs against the app's own
server-side `NEBIUS_API_KEY` — the per-practitioner BYO-key model is
retired, not renamed. This is a bigger change than "swap which key
`client_for()` reads" — it removes a whole onboarding step and a stored
field:

- **`core_store`'s `anthropic_api_key_encrypted` field** (and its
  encrypt/decrypt helpers, `_decrypt_api_key` in `app/main.py`) is no
  longer needed — every LLM call, ingestion or query-time, now goes
  through one server-side client.
- **`client_for(api_key)` (`app/llm.py:20-21`) loses its parameter** —
  there's no longer a per-caller key to optionally override with; every
  call site uses the single module-level client.
- **`profile/+page.svelte:70-76`'s "Set your Anthropic key" field is
  deleted**, not relabeled to "Nebius key" — there's nothing for a
  practitioner to set.
- **The Consult/Clients/Knowledge 403 gate tied to a missing key**
  (`(practitioner)/practitioner/+layout.svelte:6-9`'s comment references
  `require_pro_practitioner`) needs checking: if that gate was *only*
  "no key set → 403," it goes away entirely now that there's always a
  key; if it's actually gating on `plan == 'pro'` independent of the key,
  that part stays and only the key-related branch is removed.
- **[v4.1/03 CR2](../v4.1/03-known-issues-and-gaps.md#cr2--the-practitioner-onboarding-checklist-can-never-show-not-done)'s
  fix needs a follow-up edit, not a revert**: that fix made the
  "Set your Anthropic key" checklist step check real state
  (`has_anthropic_key`) instead of being permanently true. With no key to
  set, **the step itself should be removed from the checklist**
  (`dashboard/+page.svelte`'s `steps` array drops to two entries), not
  left checking a field that no longer exists.
- **Billing/cost implication, stated plainly since it's the actual reason
  this decision matters**: Nebius usage cost across every practitioner
  now runs against one shared bill instead of being distributed to each
  practitioner's own key. Noted here as a fact of the decision, not
  re-litigated — the product call was made explicitly, not defaulted into.

## Decided: what consumes the Embedder's output

"Embeds KB chunks into the database" is *additive* — the existing graph/
source-card retrieval stays the primary path, not replaced. **Database:
Neo4j's native vector index** (the graph already lives there; no
second datastore to run). **Recommended consumer, decided as the target
but not wired into the live retrieval path in this implementation pass**:
a semantic-recall booster for the retrieval planner — when graph/
keyword-based retrieval (`select_sources()`) returns few or low-confidence
candidates for a question, a vector-similarity query over embedded chunks
widens recall, merged into the same candidate set and still filtered by
the practitioner's grade threshold (so it can't bypass the trust-grading
system that's this product's whole differentiator). This directly
addresses a real, named limitation (`.env.example`'s own
*"no embeddings"* comment) rather than adding a disconnected feature.

**Implemented in this pass**: `llm.embed_passages()` (one Nebius
embeddings call per document, same batching pattern as
`extract_concepts()`) and a Neo4j vector index on `Chunk.embedding`,
written at ingest time (`knowledge.ingest_source()`). **Not implemented in
this pass**: the retrieval-planner consumption side above. Reasoning:
that change touches the live retrieval path with no way to verify it
against a real Neo4j instance in this change's environment, and a
mistake there would silently degrade every clinical answer — too high a
blast radius to ship unverified in one blind pass, per this project's own
convention of flagging consult-pipeline-adjacent changes for a live
spot-check (see [v4/04](../v4/04-known-issues.md)'s process note). The
write path alone is safe to ship: it's purely additive, and nothing
existing reads or depends on it yet.
