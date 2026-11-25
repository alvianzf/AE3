# v9/03 — Living client state (and why the specialist swarm idea was dropped)

## The brief

A follow-on to specs/v9/02: having been told to stop anchoring on the
current setup and propose the actual best architecture, two genuinely
new ideas were floated — a parallel specialist-agent swarm replacing
the single agentic loop, and a persistent "living" per-client clinical
state replacing recompute-from-scratch-on-every-consult. Instructed to
research both properly before writing either into a spec. This document
reports the result: one idea is dropped on the evidence, the other is
specced concretely.

## Specialist swarm: dropped

The proposal was three parallel agents (library specialist, patient-
history specialist, safety specialist) with a final model synthesizing
their independent findings, replacing the single generalist agentic
loop built this session.

**Why it's dropped, not built:**

- Anthropic's own published multi-agent research system data is
  explicit about where parallel decomposition wins: broad,
  independent-subtask research with no real cross-referencing need
  (their own example: "find every S&P 500 company's IT board member").
  They state plainly that the pattern struggles on tasks needing shared
  context or with genuine inter-agent dependencies — and uses roughly
  15x the token budget of a single agent even when it works.
- This app's actual shape is the weak case, not the strong one: a
  single clinical question routinely needs the library's finding and
  the patient's own history read *together* ("does this patient's
  specific medication interact with what the library says about this
  supplement") — exactly the kind of cross-referencing that isolated
  specialist contexts can't do, because neither specialist alone has
  both halves of the fact.
- The decisive evidence: a study purpose-built to test whether
  multi-agent collaboration reduces hallucination in clinical tasks
  found it **increased** hallucination in 8 of 36 comparisons and
  reduced it in only 4 — and explicitly warns that an accuracy gain
  must not be mistaken for a hallucination-rate improvement. For a
  zero-fabrication-tolerance app, a coin-flip-or-worse effect on the
  exact failure mode this app cannot tolerate is disqualifying on its
  own, independent of cost or latency.
- No source found shows a parallel specialist swarm beating a single
  agent on both net latency *and* net cost for a bounded, single-
  question task — the critical path is still roughly the slowest
  specialist plus a full synthesis call, which does not obviously beat
  today's 85-125s agentic-loop baseline.

**What the evidence does support, and is already built:** a single
agent that fans out parallel tool calls within one shared context
(this session's parallel-search fan-out fix to `AGENTIC_SYSTEM`) gets
the same concurrency benefit without fragmenting context across
isolated agents — this is a real, standard, named pattern, not a
consolation prize. The one evidenced exception for a *second* model in
the loop is a dedicated, sequential verification/audit pass — which is
exactly what `app/reasoning/citation_gate.py` already is. Nothing
changes here: the current shape was already the evidenced-correct one.

## Living client state: specced

### The actual problem

`vault.get_patient_history_up_to()` queries raw `record_entries` rows
and re-synthesizes a prose briefing via an LLM call **from scratch, on
every single consult start** — and the agentic retrieval loop's own
sense of "this patient's history" is exactly as cold-start. Nothing
about a client persists between consults except the trajectory log,
which nothing currently reads back in. This is the actual ceiling on
both latency (the briefing LLM call runs every time, not once per
change) and on "gets smarter with use" (there is currently nothing
*to* get smarter — every consult starts from the same raw rows as the
first one ever did).

### The design: bi-temporal, deterministic, disposable

Grounded in Zep/Graphiti's bi-temporal fact model (`t_valid`/`t_invalid`
for when a fact was true in the world, distinct from system time) but
explicitly **not** adopting Graphiti itself — it's built for extracting
facts from unstructured conversation via an LLM, and this app's facts
(labs, conditions, medications) already arrive typed and coded via
`vault.add_entry()`. Running an LLM-mediated contradiction-resolution
step over data that's already structured would be solving a problem
this app doesn't have, while taking on Graphiti's own documented
concurrency caveats and the exact LLM-fact-supersession reliability
risk Mem0 itself retreated from in April 2026.

**Concretely, a new Postgres table per practitioner vault** (same
schema-per-practitioner isolation every other vault table already
uses), one row per (client, marker/condition/medication):

```sql
CREATE TABLE client_clinical_state (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(id),
    kind TEXT NOT NULL,              -- 'lab_marker' | 'condition' | 'medication' | 'hypothesis' | 'action_item'
    label TEXT NOT NULL,             -- e.g. 'ferritin'
    value TEXT,                      -- current value, if applicable
    trend TEXT,                      -- 'rising' | 'falling' | 'stable' | NULL (not applicable)
    status TEXT NOT NULL DEFAULT 'active',  -- 'active' | 'resolved'
    valid_from TEXT NOT NULL,        -- when this became true (world time)
    valid_to TEXT,                   -- NULL = still current
    source_entry_id TEXT NOT NULL REFERENCES record_entries(id),  -- provenance, not optional
    updated_at TEXT NOT NULL
);
```

- **Update path is deterministic, not LLM-mediated.** When a new
  `record_entries` row of kind `lab` lands for a client, an application
  hook (not a database trigger — keeps the logic in Python, testable,
  consistent with how this codebase already handles every other
  write-time side effect) parses the labeled value, finds the prior row
  for that `(client_id, label)`, sets its `valid_to`, computes `trend`
  by comparing against it, and inserts the new current row. No LLM call
  in this path at all — this is the same lesson Mem0's retreat from
  LLM-driven consolidation already teaches, applied up front rather
  than learned the hard way.
- **`source_entry_id` is mandatory, not optional.** Every derived row
  traces back to the exact raw record it came from — directly
  addressing the provenance gap multiple sources flagged as a real,
  open limitation even in Graphiti. A practitioner (or this app's own
  future audit tooling) can always answer "where did this trend claim
  actually come from" by one join, not by trusting the derived table.
- **This table is disposable and rebuildable by construction** — the
  non-negotiable rule every architecture source converged on. It is
  never the thing written to directly by a practitioner action or read
  as sole ground truth by anything safety-critical; `record_entries`
  stays authoritative. A **periodic reconciliation job** (nightly is
  enough at this app's volume) recomputes `client_clinical_state` from
  `record_entries` for every client from scratch and diffs it against
  the live incrementally-maintained version — any mismatch is a bug in
  the hook logic, caught before a practitioner ever sees a wrong trend,
  not a silent drift. This is the specific, concrete mitigation the
  research called out as necessary given this is a clinical-safety
  application, not optional hardening.

### What consumes it

- `generate_consult_intake_summary`'s opening briefing becomes a read
  of this table (fast, already up to date) instead of an LLM
  resynthesizing a prose summary from raw rows on every consult start —
  the LLM call only needs to run again when something actually changed
  since the last read, not unconditionally every time.
- The agentic retrieval loop's implicit "patient history" context
  becomes a structured read from this table rather than
  `patient.as_query_text()`'s flat prose block — meaning the model
  receives "ferritin: falling, 4 consecutive tests, currently 8.1 µg/L,
  low" as a fact with a trend already computed, not a wall of dated
  prose it has to re-derive the trend from itself, which is both faster
  and removes a real place for the model to get the trend direction
  wrong.
- Real "gets smarter with use": the longer a client's history exists,
  the richer and more reliable `client_clinical_state`'s trend data
  gets — directly compounding with usage, the same property that made
  agentic retrieval's own continual-learning mechanism (specs/v9's
  retrieval_trajectories table) the right shape earlier in this
  session, now applied to patient data instead of retrieval behavior.

### Why this is the lightweight version, deliberately

No new infrastructure — one new table per existing per-practitioner
Postgres schema, using patterns (`CREATE TABLE`, app-level write hooks)
already used throughout `core_store.py`/`vault.py`. No new dependency,
no LLM in the write path, no Neo4j/Graphiti/Mem0 adoption. The
heavyweight version (LLM-mediated cross-document contradiction
resolution, the way Graphiti does it for unstructured text) is
explicitly not justified here, because this app's clinical facts don't
need extracting from prose — they're already typed at the point they're
recorded.

## What changes, concretely, versus v9/02

Nothing in v9/02's verdicts changes. This adds one new, concrete,
lightweight component (`client_clinical_state`) to the "do" column, and
formally closes the specialist-swarm question as researched-and-
rejected rather than leaving it open. The single-agent-plus-parallel-
tool-calls-plus-sequential-verification shape already built this
session was, per this round's research, already the evidenced-correct
answer — the gap this document closes is upstream of retrieval
entirely: what the agent is given to work with before it searches at
all.
