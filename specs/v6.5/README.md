# v6.5 — Lab intake, dedicated-deployment model routing, consult page hardening

**Status: implemented, live-verified in production.** Same week as
`v6.4`, later — the lab-intake feature `v6.4` flagged as a gap but
didn't build, a full re-shuffle of which model backs which AI-team
role (three providers now, not one), and three real consult-page bugs
found live and fixed the same day they shipped.

- [**01 · Lab intake**](01-lab-intake.md) — practitioners and clients
  can now both record patient data (labs, conditions, medications,
  notes, history). `get_patient_context()` had read these fields since
  it was written; nothing ever wrote them. New CRUD endpoints on both
  sides, privacy-scoped so a client only ever sees/deletes their own
  self-reported entries, never a practitioner's private notes.
- [**02 · Model routing**](02-model-routing.md) — the AI team now spans
  three separate deployments, not one shared catalog: a dedicated
  Qwen3-32B deployment (Reader/Graph-builder/Checker-LLM), Kimi-K3
  routed to Nebius's EU-west2 region (Reasoner/Answer Engine), and the
  original shared global endpoint (Embedder, on its own dedicated
  deployment). Real compatibility bugs found and fixed making this
  work: a second, incompatible thinking-disable mechanism, a much
  lower `max_tokens` ceiling on the dedicated deployment, and Kimi-K3
  confirmed consistently slower than Qwen3-235B in paired trials
  (a decision this document explains, not just records).
- [**03 · Consult page hardening**](03-consult-hardening.md) — three
  bugs found live the same week the chat redesign (`v6.4`) shipped:
  `general_lookup`'s "How it searched" dumping the entire conversation
  history instead of the actual question; the page auto-selecting
  whichever client sorted first instead of requiring an explicit
  choice, and losing that choice on refresh; and a genuine regression
  from the fix for the second bug — the sidebar going completely
  unclickable on first arrival, caused by an uncaught error inside a
  `$effect` silently breaking the rest of the component's reactivity.

## What this does not change

The retrieval pipeline's architecture (seed search, graph traversal,
`general_lookup`) and the Checker's LLM-as-judge design (`v6.3`) are
unchanged — this version is about *which model* backs each role and
*where it runs*, plus UI bugs, not new retrieval logic. `v6.3`'s own
status line is now stale on one point (`CHECKER_LLM_MODEL` no longer
defaults to Kimi-K3) — see `02` here for the current picture; `v6.3`
itself is left unedited per this repo's own versioning convention.
