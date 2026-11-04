# v7/01 (implemented) — Design system foundation, Phase 0

**Status: implemented.** First redesign phase, per the plan in
`07-implementation-phasing.md`. Purely additive — the spec's own
stated requirement for this phase ("zero visible change" to any
existing page) is the verification bar, not just a goal.

## What shipped

- `web/src/app.css` — every new token from `01-design-system.md`
  added to `:root`: `--weight-regular`/`--weight-medium`/
  `--weight-bold` (750 matches the heaviest weight already in real
  use, not a new value), `--duration-fast`/`--duration-base`/
  `--duration-slow` (120ms/200ms/400ms, matching literals already
  used ad hoc across the codebase), `--ease-in`/`--ease-out` (new
  curves — nothing adopts them yet), `--container-max` (extracted
  from `.container`'s previously-hardcoded `78rem`, same value). A
  documented comment block records the existing (unchanged) type
  scale's actual ratio pattern and the app's three real breakpoints
  (720px/900px/960px), each verified against the actual `@media`
  rules in `AppRail.svelte`/the admin Library page/`app.css` rather
  than assumed.
- `web/src/lib/components/EmptyState.svelte` (new) — icon + headline +
  optional supporting copy + optional action snippet. Not wired into
  any page yet — that's a later phase, once each page's existing
  empty-state copy is read and ported deliberately rather than
  swapped in blind.
- `web/src/lib/components/Skeleton.svelte` (new) — three variants
  (`line`/`circle`/`block`), a shimmer animation already covered by
  `app.css`'s existing `prefers-reduced-motion` override. Also not
  wired into any page yet.

## Verification

`npm run check` — 0 errors, identical warning count to the pre-phase
baseline (no new warnings introduced). No existing `.svelte` file's
markup or styling was touched beyond `.container`'s one-line swap to
the new `--container-max` token (value-preserving — `78rem` before and
after). No page's rendered output changes as a result of this phase.

## What this does not change

Nothing yet adopts the new weight/duration/easing tokens or either new
component — every existing page's CSS and markup is untouched. That
adoption is Phase 1 onward (`02`-`06`), each its own spec-reviewed,
separately shipped PR per `07`'s plan.
