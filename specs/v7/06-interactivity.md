# v7/06 — Interactivity: micro-animations, onboarding, command palette

Cross-cutting — applies across the public site and all three portals,
per the user's explicit priority choices (all three selected when
asked what "interactive" should include, beyond what already shipped
this week: drag-and-drop, the "⋮" menus, the force-directed Graph
view).

## Micro-animations / transitions

Current state: `app.css` already defines `liftIn`/`fadeIn` keyframes
and a documented `prefers-reduced-motion` override that collapses all
animation/transition durations near-zero — the accessibility
foundation is already correct and must not regress. What's missing is
breadth and consistency of *use*, not the mechanism itself:

- **Scroll-triggered reveals** (landing page, `02`) — today's
  entrance animations fire once on mount; an `IntersectionObserver`-
  driven variant (reusable as a small `reveal` Svelte action, not a
  new dependency) extends the same existing keyframes to "as you
  scroll," not just "on load."
- **State-transition polish**: the admin Library's view-mode switch
  (icons↔list↔table), tab switches (`Tabs.svelte`), and dialog open/
  close (`Dialog.svelte`) are instant today — a `--duration-fast`/
  `--duration-base` (from `01`) cross-fade or slide on each, consistent
  app-wide rather than ad hoc per component.
- **Loading skeletons** (`Skeleton.svelte`, from `01`) wherever a page
  currently shows nothing (or a bare "Loading…" string) while data
  resolves — the single highest-ratio "feels responsive" change
  available, and a precondition for the onboarding tour below (a tour
  step pointing at an empty/loading area reads as broken).
- **Hover/focus feedback audit**: most interactive elements already
  have `:hover`/`:focus-visible` states (the global `:focus-visible`
  outline in `app.css` is solid) — a pass to confirm every *new*
  component this week (`Menu.svelte`, the doc-card "⋮" trigger, the
  Graph view's zoom controls) matches that same baseline, since new
  components built under time pressure are exactly where this kind of
  polish is most likely to have been skipped.

## Onboarding / guided flows

New: a small `Tour.svelte` (spotlight-style — dims the page, highlights
one element at a time with a tooltip-style callout and Next/Skip
controls) plus a `data/users/me`-scoped "has this user completed the
tour for portal X" flag, persisted server-side (not `localStorage` —
a client/practitioner/admin switching devices should not see the tour
replay from scratch, and an admin reviewing a colleague's onboarding
state needs it to be durable, not per-browser).

Per-portal tour content (first draft, refined once each portal's own
page spec — `03`/`04`/`05` — is written in full):

- **Admin**: "+ Add resources" → the view-mode toggle → the Graph/Tree
  tabs → the queue status bar.
- **Practitioner**: Consult (the core loop) → the Pro-gated nav items
  and what they unlock → Knowledge (library weights).
- **Client**: "start here" on Dashboard → Questionnaire → where their
  practitioner's visibility boundary is explained in plain language
  (what the practitioner can/can't see — a trust question, not just a
  UI question).

Each tour is skippable at every step and re-launchable later (a
"Replay tour" entry, likely living in a settings/profile page or the
new command palette) — never a one-time forced gate blocking real use
of the product.

## Command palette / keyboard-first navigation

New: `CommandPalette.svelte`, triggered by `Cmd/Ctrl+K` and a visible
rail icon (per `03`'s note — a keyboard-only trigger with no visible
affordance is undiscoverable to anyone who doesn't already know to
look for it). Scope per portal:

- **Admin**: jump to a document by title (reuses the Library page's
  existing search/filter logic against `data.sources`, no new fetch),
  jump to a folder, trigger "+ Add resources," switch Library tabs
  (Library/Tree/Graph), jump to Dashboard/Users/Questionnaires/Audit.
- **Practitioner**: jump to a client by name, jump to Consult, jump to
  a specific past conversation (reuses the sidebar's existing
  searchable-client logic from `specs/v6.4`).
- **Client**: jump between the portal's 5 pages — intentionally
  minimal here, consistent with `05`'s "lower priority for this
  portal" framing.
- **Public site**: optional, lower priority (`02`) — if included,
  scoped to jumping to `/practitioners`, `/join`, `/login`.

Implementation shape: a single generic `CommandPalette.svelte` (fuzzy-
match a flat list of `{label, action, group}` entries, keyboard nav
with arrow keys + Enter, Escape to close) with each portal's
`+layout.svelte` supplying its own entry list — same "generic
component, per-call-site content" pattern `Menu.svelte` (`v6.14`)
already established, not a new architectural idea.

## What this does not change

No change to any backend route for any of the three pieces above —
the command palette's actions are client-side navigation/triggers
reusing existing handlers; the onboarding flag is the one new piece of
server state this spec calls for (a small addition to each account's
existing settings storage, not a new subsystem), named here explicitly
since `00-overview.md` states "no API changes anticipated" as the
default, not an absolute rule — this is the one call-out.
