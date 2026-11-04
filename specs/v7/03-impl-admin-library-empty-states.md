# v7/03 (implemented, partial) — Admin Library empty states, Phase 2

**Status: implemented — `EmptyState.svelte` adoption only.** The
`Card.svelte` consolidation (`.doc-card`/`.folder-card` sharing a
generic wrapper) named in `03-admin-portal.md`'s original Phase 2
description is **deliberately descoped**, not deferred by accident —
explained below.

## Scope change from the original plan

Read `.doc-card`/`.folder-card`'s actual CSS before building anything
(per `01`'s own stated norm). They are not two instances of one
pattern with cosmetic differences — they're structurally different:
`.doc-card` is a flex-column content card (`--r-lg` radius,
`--panel-2` background, inline rows for tags/grade/folder); `.folder-
card` is a centered-content clickable tile with absolutely-positioned
overlay actions (`--r` radius, `--panel` background, fixed
`min-height`, button-based interaction rather than flow content).
Forcing both into one generic `Card.svelte` based on "both have a
border and a background" would have been abstracting two genuinely
different things together — the exact "wrong abstraction" failure
mode this repo's own engineering guidance names explicitly (copy-paste
twice before you abstract), not the CSS-drift reduction the original
phasing doc's one-paragraph description assumed before this closer
read. Reversed here rather than forced through to match a plan written
before the actual code was reread.

The real, lower-risk, still-valuable win from `01`'s component
inventory for this page was `EmptyState.svelte` — that shipped
instead.

## What shipped

All three of the Library's empty-state messages (previously a single
bare `<p class="hint">` with a three-way ternary, duplicated nearly
verbatim across Icons/List and Table view) are now full `EmptyState`
instances — icon, headline, supporting copy, and (where one made
sense) a primary action button reusing the page's existing `ingestOpen`/
`q` state, no new handlers:

- **Library truly empty** (`!data.sources.length`): book icon, "Your
  library is empty," a "+ Add resources" button (opens the same
  dialog the header's own button does).
- **Search matches nothing** (`searching`): search icon, "Nothing
  matches that search," a "Clear search" button.
- **Current folder is empty** (neither of the above): folder icon,
  "This folder is empty," the same "+ Add resources" button.

A new `.grid-empty { grid-column: 1 / -1 }` rule was needed for the
Icons/List grid variant — a single item inside `.doc-grid`'s
`auto-fill` columns would otherwise only claim one narrow track's
width (16rem), which the old plain-text hint got away with but this
richer treatment visibly needed to span the full row. Table view's
instance sits inside the already-`colspan="10"` cell, no equivalent
change needed there.

The directory/topic-facet row's own separate "Nothing ingested yet"
line (`!data.coverage.length`, fires alongside the grid's own identical-
condition empty state when the library is truly empty) was
deliberately left as a plain hint, not upgraded — upgrading it too
would have put two near-identical "start here" blocks stacked on the
same screen.

## Verification

`npm run check` — 0 errors, baseline warning count (24, identical to
pre-phase). No change to any handler, state variable, or data flow —
purely a rendering swap inside three existing conditional blocks.

## What this does not change

- No `Card.svelte` built this phase — see "Scope change" above. If a
  future pass finds a real, narrower shared surface between `.doc-
  card`/`.folder-card` worth extracting (border color, transition
  timing — the properties they do actually share), that's a
  self-contained follow-up, not blocking anything here.
- `Skeleton.svelte` adoption, the command palette, and the onboarding
  tour for this portal remain future phases per `07`'s plan.
