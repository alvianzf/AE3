# v10/01 — Production drift: what v9 assumed vs. what the VPS actually runs

## Why this exists

v9 (`specs/v9/01-latency-brainstorm.md`) was written entirely from
reading the codebase — real discipline for a code-level question, but
it never looked at the actual production box. Implementing v9's
candidates A and B, and investigating candidate F per direct
instruction, meant SSHing into the VPS (`root@<prod-host>`) for the
first time this spec series has done that. Several things on the box
don't match what the codebase alone implied. This is that drift,
recorded so a future spec doesn't re-derive it from scratch or, worse,
re-assume the codebase's picture is the whole picture.

## What shipped from v9

- **Candidate A (Anthropic prompt caching)** — implemented in
  `app/clients/anthropic_client.py`: `chat_json`/`chat_text` now send
  the system prompt as a `cache_control: ephemeral` content block.
- **Candidate B (parallelize the ingest Reader call)** — implemented in
  both the live path (`app/main.py`'s `_run_ingest`) and the CLI path
  (`app/ingestion/pipeline.py`'s `ingest()`): the Reader call now runs
  concurrently with chunking+embedding instead of blocking on it first.
  A wall-clock log line was added to each path for a real before/after
  number, per v9's own acceptance bar — no live-timed trial has been
  run against that log yet; this spec does not claim the ≥30% target
  met, only that A and B are deployed.
- Both are live in production as of this writing, verified via a clean
  graceful reload in `journalctl -u clinic` and a healthy
  `GET /api/health`.

**Candidate C (formalize the local embedder as the deliberate
default) was deliberately NOT implemented** — see "Drift 1" below for
why the premise itself needs correcting, not just the quality-check
gap v9 already flagged.

## Drift 1 — Candidate C's premise was already half wrong

v9 described the local embedder as "an undocumented emergency
fallback" that candidate C would *formalize* into the deliberate
default by flipping `EMBEDDER_FORCE_LOCAL`'s default in `app/config.py`.

**What's actually on the VPS**: `/opt/clinic/.env` already sets
`EMBEDDER_FORCE_LOCAL=true`, explicitly, in the deployed environment
file — not inferred, not defaulted, read directly off the box. The
override v9 called "emergency-only" is not a code default waiting to
be formalized; it is already the actual, deliberate, currently-running
configuration, set by whoever operates this box. The only thing
candidate C would change is `app/config.py`'s *fallback* value for
when that env var is absent — which has no effect here, since the env
var is always present on production.

Confirmed directly, same session: Nebius's embeddings endpoint still
returns `402 insufficient_quota` on a real request (the same billing
exhaustion v9 noted on 2026-11-02, not yet resolved). So the local
embedder isn't a candidate to switch to — it is, right now, the only
embedder that works at all. There is no live "Nebius vs. local"
choice being made in production today; there is one embedder that
runs and one that errors.

**What this changes**: candidate C's own stated blocker (a real
side-by-side retrieval-quality check, local vs. Nebius, before
flipping the default) is unchanged and still unmet — this isn't
resolved, just reframed. What's corrected is the premise: there is no
urgency to "formalize" a default that has zero practical effect while
Nebius stays down, and the quality question is not "should we switch"
but "the thing already running has never been validated against the
thing it silently replaced." The quality check v9 asked for is still
the right next step, whenever Nebius billing is restored enough to
run it — not because the default needs flipping, but because nobody
has ever confirmed the smaller model isn't quietly missing passages.

## Drift 2 — The real constraint on candidate F is the VPS, not the code

v9 marked candidate F (raising `INGESTION_CONCURRENCY` above 1) as
"out of scope... a throughput lever, not a per-request latency one,"
correctly, but had no way to say whether raising it was actually safe
— that requires knowing the box, not the code. Checked directly:

- **2 vCPUs total.** Confirmed via `nproc`.
- **One gunicorn worker serves every live request.**
  `clinic.service` runs `gunicorn ... --workers 1`
  (`/etc/systemd/system/clinic.service`) — there is no second process
  to absorb a CPU spike; every consult, every page load, and every
  background ingestion job share the same event loop and the same two
  cores.
- **Embedding is already CPU-bound local inference**, per Drift 1 —
  not a Nebius network call. `INGESTION_CONCURRENCY` controls how many
  ingest jobs run their (now-parallel, per candidate B)
  reader+chunk+embed section concurrently; each one's embedding step
  now actually competes for CPU time on this box, not just for a spot
  in a network queue the way it would under Nebius.
- Load average at inspection time was near-zero (0.05) — idle-time
  headroom, not burst headroom. A bulk "ingest selected" action
  queuing several documents at once is exactly the scenario where
  raising concurrency would spike CPU contention against the single
  worker serving real users, at the moment an admin is least likely to
  be watching for it.

**Recommendation, unchanged from the live investigation**: leave
`INGESTION_CONCURRENCY` at its default (1). Revisit only alongside
infrastructure that adds real spare capacity (a second worker/box),
not as a same-box config bump.

## Drift 3 — Operational loose ends found, not caused, by this investigation

Noted because they're easy to trip over later, not because either
needs fixing today:

- `/etc/systemd/system/clinic.service.bak` exists on the box — an
  older unit definition (plain `uvicorn`, `MemoryMax=500M`, no
  gunicorn/worker-class line) superseded by the real, enabled
  `clinic.service` (gunicorn, `MemoryMax=6G`). It isn't loaded or
  referenced by systemd and isn't currently causing anything, but a
  future "which service file is real" debugging session should check
  `systemctl status clinic` (confirms `enabled`, the real
  `ExecStart`) rather than `ls /etc/systemd/system/clinic*`, which
  returns both.
- `/opt/clinic` is not a git checkout (`git log` there fails with "not
  a git repository"). The deploy pipeline (GitHub Actions, per
  `DEPLOY.md`) copies built artifacts rather than cloning — meaning
  there is no on-box way to directly confirm "what commit is this,"
  only the GitHub Actions run log and a live behavioral check
  (`/api/health`, `journalctl` timestamps around a known deploy time).
  Not a problem by itself, but worth knowing before reaching for
  `git log` on the box out of habit.

## What this doesn't change

- No code change from Drift 1 — `app/config.py`'s `EMBEDDER_FORCE_LOCAL`
  default is left as-is; the env var already overrides it in
  production and that's correct.
- No code change from Drift 2 — `INGESTION_CONCURRENCY` stays at its
  default of 1, nothing in `app/ingestion/queue.py` or `app/config.py`
  touched.
- No action on Drift 3's two findings — recorded, not fixed; neither
  is causing a live problem.
