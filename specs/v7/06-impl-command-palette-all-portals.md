# v7/06 (implemented) — Command palette, practitioner + client portals

**Status: implemented — all three portals now have the command
palette.** Follow-up to the admin-only version shipped earlier this
phase.

## What shipped

- `(practitioner)/practitioner/+layout.svelte`: same wiring pattern as
  admin — a `svelte:window` keydown listener, a `CommandPalette`
  instance, entries built from the rail's existing 8 nav items. Locked
  (Basic-plan-gated) items get `group: 'Pro'` in the palette instead of
  `'Practitioner'`, matching the same "(Pro)" signal the rail's own
  hover tooltip already gives for a locked icon — a palette result
  makes the same promise the icon it stands in for does.
- `(client)/client/+layout.svelte`: same pattern, 5 nav items, all
  grouped `'Client'` (no Pro-gating exists on this portal).

## Verification

`npm run check` — 0 errors, baseline warning count.

## What this does not change

Still v1/navigation-only scope, same as the admin version — no portal
gained any new in-page action triggers through the palette, only route
jumps.
