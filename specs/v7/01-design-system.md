# v7/01 — Design system foundations

Everything in this file is additive/refining to `web/src/app.css`'s
existing `:root` token block — no token is renamed or removed unless
explicitly called out, so nothing downstream breaks silently. The goal
is a documented, enforceable system in place of today's pattern (real,
but tribal — every page largely re-derives its own spacing/sizing
feel from eyeballing neighboring pages, per the comment history in
`app.css` itself: "tokens carried forward... composition redesigned").

## Color — kept as-is, scope clarified

`--bg`, `--panel`, `--panel-2`, `--line`, `--line-2`, `--ink`,
`--ink-2`, `--muted`, `--accent`, `--accent-ink`, `--accent-soft`,
`--ok`/`--ok-soft`, `--warn`/`--warn-soft`, `--danger`/`--danger-soft`,
and the `--rail-*` gradient trio are unchanged. One real gap found
while reading `GraphView.svelte` for `v6.18`: `--line-2` at 1px is
functionally invisible against `--panel` (already fixed there to
`--muted`) — audit every other `var(--line-2)` usage across the app
for the same contrast problem as part of `07`'s Phase 1, since it's
exactly the kind of bug that's easy to miss by eye in a code review
but obvious on screen.

**No dark-mode token set exists today** (`app.css` defines one `:root`
block, no `prefers-color-scheme` or `[data-theme]` overrides). Out of
scope for this redesign — raised here only so it's a visible, named
gap rather than silently assumed away; a future spec if wanted.

## Typography — a real scale, not seven ad-hoc sizes

Current: `--text-xs` (.74rem) through `--text-3xl` (2.6rem), seven
flat steps with no documented ratio between them and no weight/line-
height pairing — every component picks its own `font-weight` ad hoc
(`font-weight: 650` appears repeatedly, `700`, `750` elsewhere, no
stated reason for the specific values). Proposed:

- A documented type scale with a consistent ratio (~1.25, a standard
  "major third") from `--text-xs` up, so `--text-lg` through
  `--text-3xl` stop being hand-picked values and start being a
  derivable sequence — makes adding a genuinely new size (e.g. for a
  landing-page stat callout) a formula, not a guess.
- Three named weights only — `--weight-regular` (400),
  `--weight-medium` (600), `--weight-bold` (750, matching the
  existing heaviest value already in use) — replacing the current
  scattered 600/650/700/750 literals component-by-component.
- A documented line-height pairing per text role (tight for
  headings, relaxed for body — `body`'s existing `1.55` stays the
  body default).

## Spacing & layout — keep the scale, add container/breakpoint tokens

`--space-1` through `--space-7` stay. Add:

- Named breakpoint tokens as a comment-documented reference (the app
  already uses `720px` for the mobile rail collapse, `900px`/`960px`
  for layout-column collapses, scattered as literals across
  `AppRail.svelte`/`app.css`/various page `<style>` blocks) — not a
  CSS custom-property-driven breakpoint system (media queries can't
  read custom properties for their condition), but a single source-
  of-truth comment block plus a lint-by-grep convention so a future
  page doesn't invent an eighth arbitrary breakpoint value.
- `--container-max` extracted from `.container`'s hardcoded `78rem`.

## Elevation & motion — formalize what's already mostly consistent

`--shadow`/`--shadow-lg` and `--ease` (a custom cubic-bezier) are
already used fairly consistently. Add:

- `--ease-in`, `--ease-out` variants alongside the existing
  (effectively ease-in-out) `--ease`, for entrance vs. exit
  animations that should feel different (an entrance can ease out of
  a fast start; a dismiss should ease into a fast end) — today
  everything uses the one curve regardless of direction.
- `--duration-fast` (120ms, already the literal most hover states use),
  `--duration-base` (200ms), `--duration-slow` (400ms, matching
  `liftIn`'s existing `.4s`/`.5s`) — named durations instead of a
  literal per rule.
- A documented `prefers-reduced-motion` contract (the existing global
  override in `app.css` already collapses all animation/transition
  durations to near-zero — keep this, just document it as the
  system's accessibility guarantee so new motion work in `06` doesn't
  accidentally bypass it with an un-overridable JS-driven animation).

## Component pattern library

The real structural change. Today, `Button.svelte`/`Dialog.svelte`/
`Menu.svelte`/`Chip.svelte`/`TextField.svelte`/`Select.svelte`/
`Toggle.svelte`/`Tabs.svelte`/`DataTable.svelte`/`StatTile.svelte`
exist as genuinely shared components, but a meaningful share of the
app's visual surface is still page-local `<style>` blocks re-deriving
similar-but-not-identical versions of the same pattern — the clearest
example from this week's own work: the admin Library page
(`+page.svelte`, ~2000 lines) has its own `.doc-card`, `.folder-card`,
`.staged-row`, `.queue-status-row` styling that doesn't live in any
shared component, because the page predates a few of today's patterns
and grew incrementally rather than by design.

Proposed new/promoted shared components (each gets its own page-level
spec entry once scheduled — this is the inventory, not the full
design):

- **`Card.svelte`** — a single source for the "bordered, rounded,
  `--panel`/`--panel-2` surface" pattern currently re-implemented as
  `.card-panel`/`.panel`/`.doc-card`/`.pillar`/`.stat-tile`-adjacent
  CSS in at least four different files.
- **`EmptyState.svelte`** — every portal has at least one "nothing
  here yet" message (`Nothing ingested yet`, `Nothing staged`, a
  client with no records, etc.), each written as a bare `<p
  class="hint">` with different copy conventions. A real empty-state
  component (icon + headline + supporting line + primary action)
  is one of the single highest-leverage "not confusing" wins available
  — it's the first thing a brand-new admin/practitioner/client sees on
  nearly every page.
- **`Skeleton.svelte`** — loading placeholders. Today, a slow load
  mostly shows nothing until data arrives (or a bare "Loading…" string
  in a couple of spots) — skeletons are one of the cheapest "feels
  responsive" wins and directly serve the micro-animation priority
  from `06`.
- **`Breadcrumb.svelte`** — the admin Library page hand-rolls its own
  breadcrumb row (`.breadcrumb-row`/`.breadcrumb`); worth promoting
  once a second page needs the same pattern (the Graph view's folder
  navigation is a candidate).
- **`CommandPalette.svelte`** — new, detailed in `06`.

## What this does not change

No change to any backend contract, no change to the existing shared
components' public prop APIs (only their internal styling, where a
given page-spec calls for it) — `Button`/`Dialog`/`Menu`/etc. keep
working for every existing call site unless a specific migration is
named in a later phase.
