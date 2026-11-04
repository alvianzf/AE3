# v6.17 — Table view action parity

**Status: implemented.**

- [**01 · Table view action parity**](01-table-view-action-parity.md)
  — the full spec: the deferred `v6.16` finding this closes (Table
  view missing private/public, Edit access, Assign uploader, and all
  visibility into the in-progress queue), and what's still out of
  scope.

## Baseline this builds on

- `v6.14`'s `Menu.svelte` "⋮" dropdown — reused verbatim in Table
  view's action cell, same item set as Icons/List.
- `v6.12`'s auto-ingest queue (`data.staged`, `jobsByStagedId`,
  `jobLabel`/`jobProgressPercent`) — Table view's new staged rows
  reuse this directly, no new state.

## What this does not change

No change to the queue/job data model or `Menu.svelte` itself — see
`01`'s "What this does not change" for the rest, including which
`v6.16`-deferred items remain deferred.
