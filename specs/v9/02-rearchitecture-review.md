# v9/02 — Full-stack rearchitecture review: language, frameworks, infra

## The brief

"You are a Computer Science PhD... research the internet and journals...
Find the best way to achieve the goal of the app. Whether you need a
different tool, app, or libraries, it's OK not to base your assumptions
to the current setup... You can even propose changing the app from
Python to Rust if it makes the app better." No constraint on keeping
the current stack — the mandate was to evaluate everything, including a
full rewrite, against real 2025-2026 evidence, not assumption.

This is a decision document, not a survey. Each section ends with a
verdict — do it, defer it, or don't — not a menu. The research backing
every claim below (sources, exact benchmark numbers, case-study detail)
lives in this session's full research compilation; this document is the
synthesis and the call, made by reading that research directly rather
than delegating the judgment.

## The one load-bearing fact that shapes every verdict below

This app's request latency is dominated by multi-second external LLM
API round-trips (Anthropic/Nebius), not local computation. A consult
takes 50-125 seconds end to end; of that, essentially all of it is
waiting on a network call to someone else's GPU cluster. There is no
CPU-bound hot path of any real size — ingestion-time PDF/entity
extraction is batch, not request-path; the one genuinely CPU-bound
thing in the whole app (the emergency local-embedder fallback) is a
384-dim sentence-transformer model, not a reason to rearchitect
anything. Every verdict below follows from taking this fact seriously
instead of reasoning about this app as if it were a typical web backend.

---

## 1. Language: stay on Python. This is not close.

**Verdict: do not rewrite in Rust (or Go). Revisit only if a specific,
measured precondition below actually materializes.**

The case for Rust rests on two real, cited 2025-2026 precedents —
Discord's Go→Rust Read States rewrite and OpenAI's 2026 Habitat
(Python→Rust) rewrite — and neither one's root cause exists in this
app:

- **Discord's rewrite** was driven by GC pause spikes (p99 ~95ms) under
  a huge in-memory LRU cache in a hot read path. This app has no large
  hot in-memory cache and no GC-pause-sensitive path — every expensive
  operation is an awaited network call, not CPU work competing with a
  garbage collector.
- **OpenAI's Habitat rewrite** (2 engineers, one quarter) was driven by
  Python's *async runtime itself* failing under extreme scale —
  connection-pool metastability and thundering-herd failures at
  >1-billion-weekly-user, tens-of-millions-of-requests-per-second
  traffic. This app serves tens to low hundreds of consults/day on one
  2-vCPU VPS. The precondition that made Habitat's rewrite pay off
  (the async runtime itself becoming the bottleneck under extreme
  concurrency) is not within several orders of magnitude of existing
  here.

Separately, a direct benchmark at realistic mixed-I/O load (500 req/s)
found **p50 latency within 1ms across Python, Go, and Rust** (24.8ms /
23.9ms / 24.0ms) — because the upstream wait dominates regardless of
language. The 2-2.6x throughput gaps language benchmarks report are
measured on near-zero-latency endpoints (a bare `/health` check); they
describe framework floor overhead, not what happens when every request
spends 20-100 seconds waiting on Anthropic.

Against this, the cost of a Rust rewrite here is concrete and immediate,
not hypothetical:
- **No official Anthropic Rust SDK exists.** The app's entire value
  proposition — grounded, cited, anti-fabrication-constrained clinical
  answers — runs on Claude. A rewrite would mean depending on one of a
  small number of unofficial, single-maintainer Rust wrappers for the
  exact capability (tool use, prompt caching, streaming) this session
  spent real effort getting right in Python, with an official SDK, this
  week.
- **Neo4j's Rust driver is community-maintained only**, not
  vendor-backed the way the Python driver is.
- **Team size.** The industry's own converging decision criteria for
  "should you rewrite in Rust" explicitly name team capacity as a core
  factor — a second language's ramp-up and ongoing maintenance burden
  falls disproportionately hard on a small team, and this is a small
  team.
- The self-published "we rewrote it in Rust" blog posts that do report
  big wins are explicit, in at least one case, that the speedup didn't
  matter because the bottleneck was never the backend language in the
  first place — exactly the pattern to watch for here.

**What would actually change this verdict:** a *measured* CPU or memory
bottleneck under real production load that async/connection-pool tuning
and horizontal scaling (adding a third gunicorn worker, say) can't fix;
self-hosting model inference (not on the roadmap); or request volume
growing by orders of magnitude such that framework-floor overhead, not
LLM latency, becomes the dominant cost. None of these are close to true
today. Don't rewrite pre-emptively for a scale this app isn't at.

## 2. Async-ification of the Python backend: measure first, don't convert wholesale

**Verdict: do not do a blanket sync→async conversion right now. Do
measure the actual concurrency ceiling before deciding anything.**

The mechanistic case for async (an event loop holds many more
concurrent slow-waiting requests than a thread-per-request model,
because threads carry real OS-level overhead an event loop doesn't) is
real. But the single most consistently-repeated finding in the current
literature is the opposite risk: **mixing a blocking driver (this app's
synchronous Neo4j driver, psycopg2) inside an `async def` route blocks
the entire event loop, not just that request** — a half-converted async
app can be *worse* than staying fully sync, because one slow request
can stall every other concurrent request instead of only blocking its
own thread.

This app's current shape — sync `def` routes, Starlette's threadpool
offload, 2 gunicorn workers (bumped from 1 this session) — is actually
the *safer* intermediate state, not a liability to fix reflexively. The
real open question the research couldn't answer with a number (no
source gives a threadpool-ceiling figure for a 2-vCPU box) is whether
that threadpool is ever actually saturated under this app's real
concurrent load. That's a measurement, not a guess:

**Action:** before converting anything, instrument and watch
`gunicorn`'s worker thread-pool utilization under real concurrent
traffic (how many consults are genuinely in flight at once, how close
that gets to the threadpool's size). If it's never close to saturated,
there's no concurrency problem to solve. If it is, the fix is a fully
async rewrite of the hot path end-to-end (async Neo4j driver, asyncpg,
async Anthropic/OpenAI client) — not a partial one, since a partial
conversion is the one thing the evidence says is worse than doing
nothing.

## 3. Durable execution for the agentic retrieval loop: defer, but DBOS is the right shape when it's needed

**Verdict: don't adopt now (agentic retrieval is still shadow-mode, not
production-exposed). When it does go live, prototype DBOS specifically,
not Temporal, because it piggybacks on Postgres this app already runs.**

This is a genuinely new risk this session's own work introduced: the
agentic retrieval loop (`app/retrieval/agentic.py`) is a multi-step
pipeline making several sequential external API calls per consult, with
*no* checkpoint/resume if the process dies mid-loop — a server restart
or crash between turns loses the whole in-flight consult with no
record of how far it got. The old fixed pipeline had the same
theoretical exposure but far fewer sequential steps and much shorter
total duration, so the actual blast radius of a mid-flight crash is
larger now than it was before this session's changes.

Durable execution for exactly this problem (long-running, multi-step,
externally-dependent agent pipelines) is a real, current, actively
developing 2025-2026 category — not vaporware. Temporal's LangGraph
plugin reaching Public Preview and DBOS/Restate/Inngest being
repeatedly named together as "the durable AI agent" category are real,
verifiable, recent facts. Two real options surfaced:

- **Temporal (+ LangGraph plugin)**: the more mature, more capable
  option, but it's a new always-on orchestrator service to run and
  operate — real new infrastructure for a small team on one VPS, and a
  documented integration friction point exists (LangGraph reads
  environment state at graph-build time in a way that can break
  Temporal's deterministic-replay sandbox).
- **DBOS**: a *library*, not a new service — it checkpoints
  workflow/step state directly in Postgres tables. This app already
  runs Postgres for everything else. Adopting DBOS adds a durability
  layer without adding a new always-on service to operate, which is a
  meaningfully lower-friction fit for this team's size than standing up
  Temporal.

**Why defer rather than build now:** the agentic loop hasn't replaced
the production consult path yet — it's still being shadow-evaluated.
Building durability for a path that isn't live yet is solving a problem
that doesn't have real users behind it. The right trigger is: the
moment agentic retrieval's shadow-eval results justify making it the
default path (per the migration plan already in this session's earlier
decision), durability should be built *before* that flip, not after a
real crash loses a real practitioner's in-flight consult.

## 4. Structured-output/agent-framework libraries (Pydantic AI, Instructor, DSPy, LangGraph): don't adopt

**Verdict: keep the hand-rolled JSON-schema prompting and the hand-rolled
agent loop. No identified pain point justifies the dependency.**

Per this project's own standing principle (every dependency is
permanent code you don't control — add one only when there's a stated
reason, not "it's what people use now"): none of these libraries solve
a problem this app is actually having. The hand-rolled
`chat_json`/`chat_agentic` methods on both LLM clients work, are fully
understood by this (small) team, have real test coverage, and handle
this app's actual provider-switching requirement (Anthropic ↔ Nebius)
in a way a third-party framework would have to be bent to fit, not the
other way around.

The evidence for these libraries is opinion-heavy, not settled
consensus, and the strongest signal in the research is a *warning*: the
LangGraph literature is explicitly self-contradictory across real
practitioner accounts — some removed it as net-negative framework
overhead on exactly this kind of project shape, others only became
converts once they hit state/persistence complexity well above what
this app's current agent loop needs. Concrete reported costs (3-5 days
to get state-schema design right, 1-2 weeks team ramp-up, "30-50% more
developer time" than hand-rolling for a first LangGraph agent) are real
money for a small team, spent on a framework this app's actual
complexity doesn't yet need.

**What would change this:** if the agent loop's complexity grows
materially (genuine branching logic, human-in-the-loop approval gates,
many more tool types) to the point where hand-rolled state management
becomes the thing slowing the team down — that's the threshold the
research itself identifies as where LangGraph-style frameworks start
paying for themselves. Not there yet.

## 5. Neo4j: real opportunity to simplify, gated on the agentic shadow-eval's outcome

**Verdict: don't touch it today. Once agentic retrieval replaces the old
pipeline as default, seriously evaluate dropping Neo4j for the pgvector
path this app already has built and working.**

This session's own architecture decision already established that
graph-hop traversal (Neo4j's actual retrieval-time job) is being
replaced by agentic tool-use search, not extended. What's left using
Neo4j in the agentic design is `get_document` (full document text) and
`find_similar` (the vector index) — both of which have a working,
already-built, Neo4j-free equivalent in `app/retrieval/pgvector_store.py`
(the existing "general lookup" fast path), including the same
privacy/folder/grade semantics.

Meanwhile, Neo4j carries real, ongoing cost that's easy to undercount:
entity/relationship extraction at ingest time costs *at least 2 extra
LLM calls per chunk* (one for entities, one for relationships) beyond
the single embedding call vector-only RAG needs — a cost paid on every
single document ingested, specifically to build a graph whose primary
query-time use case (hop traversal) this app has already moved away
from. Neo4j's own vendor materials position Community Edition
(what this app runs) as suitable for "small projects, learning, and
prototyping," not as a recommended production tier — a signal worth
taking seriously given this app does run live clinical consults.

**Why gate this on the shadow-eval, not do it now:** the Neo4j Entity
graph is still being read by `get_document`/`find_similar`, and the old
graph-hop pipeline is still the production default. Dropping Neo4j
before confirming agentic retrieval actually replaces it would be
cutting the floor out from under the thing still serving real
consults. Once the shadow-eval shows parity-or-better and the switch
is flipped (per the existing migration plan), re-evaluate whether
Document/Chunk storage can move entirely to Postgres+pgvector,
decommissioning Neo4j's ingest-time entity-extraction cost and
self-hosted-graph-database operational burden entirely — not before.

## 6. Observability: adopt the OTel GenAI shape now, not a dedicated tool

**Verdict: don't adopt Langfuse/Arize Phoenix/LangSmith today. Do shape
any new logging (the `retrieval_trajectories` table added this session,
and any future tracing) around OpenTelemetry's GenAI semantic
conventions, so switching to a dedicated backend later is plumbing, not
a rewrite.**

This app already takes observability more seriously than most apps its
size by default — the SSE step-timing events, per-role token tracking,
and this session's new `retrieval_trajectories` log table all predate
any "we should add observability" conversation, because clinical-safety
auditability (what was searched, what was cited, what was flagged) is a
stated product requirement here, not an afterthought. The real open
question is whether a *dedicated* tool is worth adopting on top of
that, and the research is explicit that no source answers this
small-team-scale question directly — the available comparisons are
tool-vs-tool, not tool-vs-hand-rolled-logging-at-this-scale.

Given that gap, the responsible move isn't "adopt nothing forever" or
"adopt a tool because the category is trendy" — it's a no-regret,
near-zero-cost hedge: structure new log fields (model name, token
counts, tool/agent step names, latency) using OTel's `gen_ai.*`
attribute names where a natural mapping exists, even while still
writing to this app's own Postgres tables, not a collector. One source
frames OTel support as something that "should be a hard buying
requirement" for any tool adopted later, specifically to avoid
vendor lock-in — shaping the data this way now means that requirement
is already met whenever (if ever) a dedicated backend becomes worth
the cost. The Langfuse/ClickHouse acquisition (January 2026) is a real,
recent reminder that vendor/ownership risk in this space is not
theoretical.

---

## Summary table

| Area | Verdict | Trigger to revisit |
|---|---|---|
| Python → Rust/Go | **Don't.** Evidence converges hard against it at this app's shape and scale. | A *measured* CPU/memory bottleneck tuning can't fix, or order-of-magnitude traffic growth |
| Sync → async backend | **Don't, yet.** Measure threadpool saturation first. | Real evidence the threadpool is a concurrency ceiling |
| Durable execution (DBOS) | **Defer.** Right shape, wrong time — agentic retrieval isn't live yet. | The moment agentic retrieval becomes the default consult path |
| Pydantic AI / Instructor / DSPy / LangGraph | **Don't.** No pain point these solve today. | Agent loop complexity genuinely outgrows hand-rolled state |
| Neo4j | **Don't touch today.** Real opportunity, wrong time. | Agentic shadow-eval confirms parity-or-better over the old pipeline |
| Dedicated observability tool | **Don't adopt; do shape data as OTel-compatible now.** | Team/scale grows past what hand-rolled logging can answer |

The common thread: every "don't" above is a "don't yet, and here's the
specific, checkable condition that would change the call" — not a
blanket rejection of the category. The common thread in the "do"s this
session already shipped (the agentic retrieval build, the latency
fixes, the live bug fixes) is that they were each built in response to
a real, measured problem, not a plausible-sounding future one. This
document's recommendations follow the same discipline.
