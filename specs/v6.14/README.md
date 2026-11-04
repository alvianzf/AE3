# v6.14 — Doc-card "⋮" menu, uploader claim/assign

**Status: implemented.**

- [**01 · Doc-card menu + uploader assignment**](01-doc-card-menu-and-uploader-assignment.md)
  — the full spec: the new generic `Menu.svelte` (native `popover`,
  not a hand-rolled dropdown), and why uploader assignment is a manual
  admin override rather than a backfill — the audit log was checked
  live and found to carry no real per-user attribution for ingest
  events at all.

## Baseline this builds on

- `v6.11/01`'s `Document.uploaded_by` and the Reader-suggestion /
  admin-edit-always-wins pattern — assignment here follows that same
  shape, just with nothing for the Reader to suggest.
- `Dialog.svelte`'s native-element-over-hand-rolled-modal precedent —
  `Menu.svelte` makes the same call for `popover` vs. a dropdown.

## What this does not change

No change to the table view's action icons, or to `uploaded_by`'s
automatic capture at ingest time — see `01`'s "What this does not
change" for the rest.
