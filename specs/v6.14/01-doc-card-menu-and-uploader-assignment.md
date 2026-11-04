# v6.14/01 — Doc-card "⋮" menu, uploader claim/assign

## What

Two direct requests, handled together since the second fits naturally
inside the first:

1. "For card icons, let's have a three dots with dropdown so that it
   will be tidy." The admin Library's doc-card had grown to 5-6
   always-visible icon buttons (View, Move, Private/Public toggle, Edit
   access, Delete — on top of the finalize bell from `v6.12`). Replaced
   with a single "⋮" (`Menu.svelte`, new, generic) opening a dropdown
   with the same actions as labeled rows. The bell stays outside the
   menu, always visible when present — a notification, not a routine
   action, shouldn't be buried.
2. "For who uploaded it, match the audit log with documents uploaded,
   and input the information there." Checked before writing anything:
   the audit log can't actually answer this. Every `"ingest"`
   `:AuditEvent` has `actor` hardcoded to the literal string
   `"admin"` (`app/graph/store.py`'s `ingest_document()`), never the
   real uploader — verified live against production (21/21 ingest
   events, `actor: "admin"`, no exceptions). There is no real
   per-document uploader history to recover for anything ingested
   before `v6.11`'s `uploaded_by` capture (and the `staged_sources` row
   that briefly held the real `created_by` is deleted once ingestion
   succeeds, so that's gone too). Asked the user how to handle it;
   chosen: leave blank by default, but let an admin claim or assign a
   name/email manually. New `PATCH /api/sources/{id}/uploaded-by` +
   `store.set_uploaded_by()`, same "admin's edit is final" shape every
   other editable field here already has — reachable from the new "⋮"
   menu ("Assign uploader…" / "Reassign uploader…").

## `Menu.svelte`

Built on the native `popover` attribute, not a hand-rolled click-
outside/Escape/z-index listener set — the browser already gives a
popover light-dismiss and top-layer stacking for free, the same reason
`Dialog.svelte` already leans on `<dialog>` instead of reimplementing a
modal. Positioned with a plain CSS override (`position: absolute`
relative to the wrapper, anchored to the trigger's bottom-right) rather
than full CSS anchor positioning, which isn't reliably supported across
browsers yet — a card-corner menu never needs to flip sides, so the
simpler approach is enough.

Generic: takes a `label` (for the trigger's `aria-label`/`title`) and
an `items` snippet, so each call site renders its own `<button>`/`<a>`
items (varying danger styling, conditional items, whatever `onclick`
it needs) rather than being constrained to a fixed `{label, onclick}[]`
shape. Scoped to the doc-card for now (the one place with enough
actions to actually need tidying) — folder-card-actions and the staged
item's single Discard button weren't touched, neither had the clutter
this was fixing.

## What this does not change

- No change to the table view's row actions (View/Move/Delete, 3
  icons) — not what was flagged as cluttered, left alone.
- `uploaded_by` itself (the field, its automatic capture at ingest
  time) is unchanged from `v6.11` — this only adds a manual override
  path for documents that field never reached.
