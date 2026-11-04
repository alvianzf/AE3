# v6.17/01 — Table view action parity

## What prompted this

`v6.16`'s reconciled PM+QA audit named this the single biggest
standing gap, deliberately deferred at the time rather than rushed:
Table view's row actions were hardcoded to View/Move/Delete only —
Make private/public, Edit access, and Assign/Reassign uploader (all
available via the "⋮" menu in Icons/List since `v6.14`) simply didn't
exist there, with no indication to the admin that switching view modes
cost them those capabilities. Table view also had zero visibility into
the in-progress ingest queue — no pending-item rows, no per-item
Retry/Discard, only the aggregate status bar.

## What changed

- Table view's action cell now uses the same `Menu.svelte` "⋮"
  dropdown Icons/List already use, with the identical item set: View,
  Move to folder, Make private/public, Edit access (when private),
  Assign/Reassign uploader, Remove from library. One shared markup
  block, not two copies maintained in parallel — copy-pasted here
  rather than extracted into a snippet/component only because Svelte
  snippets aren't yet shareable across files without a dedicated
  wrapper component, and a two-call-site duplication was judged not
  worth that extra indirection for this size of block.
- Added a small lock-icon badge next to the title in Table view when
  `is_private` is true — Icons/List already show this via a "private"
  `Chip` in the card foot; Table view previously gave the admin a way
  to *toggle* privacy via the new menu but no way to *see* current
  state in the row itself.
- Staged/in-progress items now render as rows in Table view too (same
  root-only, non-searching condition the Icons/List pending cards use)
  — filename, a compact inline progress bar or error message, and
  Retry/Discard actions. Reuses the same `jobsByStagedId`/`jobLabel`/
  `jobProgressPercent`/`ingestOne`/`discardStaged` the card version
  already calls; nothing new on the data side.

## Also fixed in this pass: Menu.svelte rendered open by default

Found live while testing this: every "⋮" menu across the whole app
(not just the new Table view rows — Icons/List had the same bug since
`v6.14`) rendered **already open** on page load. Root cause:
`Menu.svelte`'s base `.menu-pop` CSS rule set `display: grid`
unconditionally, with a separate `.menu-pop:popover-open { display:
grid }` rule that was therefore entirely redundant. Author-origin CSS
always wins over the browser's own UA stylesheet regardless of
selector specificity, so that unconditional `display: grid` overrode
the native `[popover]:not(:popover-open) { display: none }` default
every popover otherwise gets for free — the exact mechanism `Menu.svelte`
was built to rely on. Fixed by removing `display` from the base rule,
leaving it set only on `:popover-open`.

## What this does not change

- No change to the underlying queue/job model, `Menu.svelte` itself,
  or any backend route — this is purely Table view's own markup
  catching up to what Icons/List already had.
- Tags stay comma-joined/read-only in Table view (unchanged) — editing
  them still means switching to Icons or List, same as before this
  spec; not part of "action parity" since tag editing was never an
  icon-row action to begin with (it's a dedicated inline input in the
  card body).
- Bulk actions (still private/public only, per `v6.16`'s deferred
  list), search not working in Tree/Graph tabs, and the other items
  `v6.16` deferred remain deferred — this spec is scoped to the one
  named gap, not a second full audit pass.
