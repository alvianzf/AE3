# v6.4 — Consult page as a chat interface, and a hallucination fix

**Status: implemented, live-verified in production.** Same day as
`v6.3`, different scope: the consult UI itself, plus a real correctness
bug found while using it.

- [**01 · Consult chat redesign**](01-consult-chat-redesign.md) — the
  consult page rebuilt as a GPT/Claude-style chat interface: a
  persistent sidebar (searchable client list, per-client conversation
  history with calendar-style date badges, a patient info widget) and
  a chat column with the composer pinned to the bottom. Markdown
  rendering, a running-step spinner, timestamped chat bubbles, a mode
  toggle (deep research / general lookup) replacing a dropdown, and a
  closed-by-default sources accordion were added across several same-
  day iterations. Two live bugs found and fixed along the way: a CSS
  grid/flex `min-width: auto` overflow (the composer rendered
  overlapping the sidebar) and 0-turn "ghost" sessions cluttering the
  history list.
- [**02 · Hallucination on topic-adjacent context**](02-hallucination-fix.md)
  — a real question ("What dietary changes would help with the
  reported bloating?") got an answer built from topic-adjacent context
  (sleep hygiene, PCOS/metformin) that never actually covered bloating,
  instead of the Reasoner admitting the library has nothing on it.
  Fixed in the Reasoner's own system prompt. Also fixes two citation-
  parsing bugs found while verifying it: the `sources` list included
  every retrieved node instead of only the ones actually cited, and
  the citation-matching regex (both server- and client-side) missed
  citations the Reasoner grouped into one bracket ("[K1, K3]").

## What this does not change

The retrieval pipeline itself (seed search, graph traversal,
`general_lookup`) and the Checker (`v6.3`'s LLM-as-judge, still the
default) are untouched — this is a UI layer and a prompt/parsing fix,
not a retrieval architecture change.
