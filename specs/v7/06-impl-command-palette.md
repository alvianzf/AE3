# v7/06 (implemented, partial) — Command palette, Phase 6

**Status: implemented for the admin portal only.** Per `07`'s own
stated sequencing (build once against the richest portal first, wire
into the other two afterward) and the Phase 3 finding that the
remaining admin/practitioner pages read this session didn't have
further safe content wins available — this phase jumped ahead of
Phases 4/5 rather than wait on them.

## What shipped

- `web/src/lib/components/CommandPalette.svelte` (new) — `Cmd/Ctrl+K`
  opens a search-first dialog (built on the same native `<dialog>`
  pattern `Dialog.svelte` already uses — not the `popover` attribute
  `Menu.svelte` moved away from after a live reliability report;
  `<dialog>` has no equivalent history of trouble in this app). Fuzzy-
  matches a flat `{label, href, icon?, group?}` list by substring
  against label and group, arrow-key navigation (clamped at the ends,
  not wrapping — the more predictable, more common palette behavior),
  Enter navigates via `goto()`, click-outside/`Escape` close it
  (native `<dialog>` behavior, same as `Dialog.svelte`).
- **v1 scope is navigation only** — jump to a route, nothing more. A
  portal's page-local state (a dialog, a tab selection) isn't reachable
  from the `+layout.svelte` level this is wired at, one level above
  any single page. Deliberately not attempted here; fuzzy-matching
  routes/labels already delivers "jump to X" without it.
- `AppRail.svelte` gained an optional `onCommandPalette` prop — when
  supplied, a visible search-icon trigger button renders in the rail
  (next to the portal label), not just the keyboard shortcut. Omitted
  entirely (not just hidden) for a portal that hasn't wired this up
  yet, so every other portal's `AppRail` usage is unchanged.
- Wired into `(admin)/admin/+layout.svelte`: a `svelte:window` keydown
  listener for the shortcut, the `CommandPalette` instance, and an
  entry list built from the rail's existing 5 nav items (Dashboard,
  Library, Users, Questionnaires, Audit history).

## Verification

`npm run check` — 0 errors, baseline warning count (24, unchanged).

## What this does not change

- Not wired into the practitioner or client portals yet — per `07`'s
  plan, that's the natural next step, reusing this exact component
  with each portal's own entry list.
- No deep-link entries for the Library page's own view modes/tabs
  (Tree view, Graph view) — those aren't separate routes today. A
  query-param-addressable version is a reasonable later follow-up, not
  built in this first pass.
- `Dialog.svelte`/`Menu.svelte` are untouched — `CommandPalette`
  copies the proven `<dialog>` pattern rather than extending either
  existing component, since its layout (search input + a results list,
  no footer/action-button row) doesn't fit `Dialog.svelte`'s existing
  header/body/footer structure.
