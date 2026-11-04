# v6.19 — Local embedder OOM fix, menu reliability rewrite

**Status: implemented.**

- [**01 · Local embedder OOM fix, menu reliability rewrite**](01-local-embedder-oom-and-menu-reliability.md)
  — two production incidents found and fixed live: a crash-loop OOM
  (502 Bad Gateway) root-caused to an unbatched local-embedder forward
  pass over an entire large book's passage list, and `Menu.svelte`
  rewritten off the native `popover` attribute onto explicit state
  after a live report that it didn't open on click.

## Baseline this builds on

- The emergency local-embedder fallback (`app/clients/
  local_embedder.py`, a prior session's work) — this fixes a real bug
  in it, not its existence.
- `v6.14`'s `Menu.svelte` (native `popover`) and `v6.15`'s fix to it —
  both superseded by this version's explicit-state rewrite.

## What this does not change

No change to `Menu.svelte`'s public API, the ingestion queue's
concurrency model, or `EMBEDDER_FORCE_LOCAL`'s on/off state — see
`01`'s "What this does not change" for the rest.
