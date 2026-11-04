# v7 — UI/UX redesign

**Status: spec only — not implemented.** Written per explicit
instruction ("create the specs first, do not implement"). Nothing in
this version has been built; implementation begins only once these
documents are reviewed and approved, phase by phase, per
`07-implementation-phasing.md`.

- [**00 · Overview**](00-overview.md) — what prompted this, scope (all
  four surfaces, one combined spec), the user's explicit direction
  choices (keep the current brand, modernize execution; prioritize
  micro-animations, onboarding, and a command palette), and what this
  explicitly is not (no rebrand, no backend changes, no single giant
  PR).
- [**01 · Design system foundations**](01-design-system.md) — the
  shared type scale, spacing/breakpoint documentation, motion tokens,
  and new/promoted component inventory (`Card`, `EmptyState`,
  `Skeleton`, `Breadcrumb`, `CommandPalette`) every other section
  builds on. **Phase 0 implemented** — see
  [01-impl-design-system.md](01-impl-design-system.md).
- [**02 · Public site**](02-public-site.md) — landing page (icon
  pillars, a real product glimpse, scroll-triggered reveals),
  `/practitioners`, `/join`/`/login`/`/signup`, `PublicNav.svelte`.
  **Phase 1 implemented, partial** (icon pillars + scroll reveals
  only — the product glimpse and social proof remain a content
  decision for the user) — see
  [02-impl-landing-page.md](02-impl-landing-page.md).
- [**03 · Admin portal**](03-admin-portal.md) — Library (highest
  priority: component consolidation, not new features), Dashboard,
  Users, Questionnaires, Audit history, the nav rail. **Phase 2
  implemented, partial** (`EmptyState.svelte` adoption across all
  three of the Library's empty states; `Card.svelte` consolidation
  deliberately descoped after a closer read found `.doc-card`/
  `.folder-card` are genuinely different patterns, not one pattern
  with cosmetic drift) — see
  [03-impl-admin-library-empty-states.md](03-impl-admin-library-empty-states.md).
- [**04 · Practitioner portal**](04-practitioner-portal.md) —
  Consult first, then Clients/Knowledge and the rest.
- [**05 · Client portal**](05-client-portal.md) — the least
  technically-sophisticated audience; onboarding prioritized over the
  command palette here specifically.
- [**06 · Interactivity**](06-interactivity.md) — the three
  cross-cutting priorities the user named: micro-animations/
  transitions, onboarding/guided flows, command palette/keyboard
  navigation. **Phase 6 implemented, partial** (command palette —
  admin portal only; practitioner/client portals follow) — see
  [06-impl-command-palette.md](06-impl-command-palette.md).
- [**07 · Implementation phasing**](07-implementation-phasing.md) —
  the shipping plan: 8 phases (design system → landing page → admin
  Library → rest of admin → practitioner → client → command palette →
  onboarding), each its own reviewable PR, no phase merging without
  explicit user confirmation.

## Baseline this builds on

Every existing design token in `web/src/app.css`, every existing
shared component (`Button`, `Dialog`, `Menu`, `Chip`, `TextField`,
`Select`, `Toggle`, `Tabs`, `DataTable`, `StatTile`), and the current
brand identity (rose/pink gradient rail, `Sprig` mark, warm cream
surfaces) — kept, not replaced, per the user's explicit choice.

## What this does not change

No backend route, data model, or business-logic change anticipated
anywhere in this version (the one named exception — a small per-
account "has completed onboarding" flag — is called out explicitly in
`06`). No rebrand. No single giant PR — see `07` for the real shipping
plan.
