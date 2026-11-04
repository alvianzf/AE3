# v7 — UI/UX redesign: overview

**Status: spec only — not implemented.** Per explicit instruction
("create the specs first, do not implement"), this version is
scoping/design documentation. Implementation starts only once these
specs are reviewed and approved, page by page, in the phased order
`07-implementation-phasing.md` lays out.

## What prompted this

Direct request: act as UI/UX and redesign "the whole thing including
the landing page" — interactive, user-friendly, not confusing, modern,
professional.

## Scope

All four surfaces, one shared design language:

- **Public site** (`web/src/routes/(public)/*`) — landing page,
  `/about`, `/join`, `/login`, `/signup`, `/practitioners`,
  `/account`, `/coach`
- **Admin portal** (`(admin)/admin/*`) — Library (the most complex
  single page in the app after this week's work: icons/list/table
  views, Tree view, Graph view), Dashboard, Users, Questionnaires,
  Audit history
- **Practitioner portal** (`(practitioner)/practitioner/*`) —
  Dashboard, Clients, Consult, Contacts, Knowledge, Questionnaires,
  Profile, Upgrade
- **Client portal** (`(client)/client/*`) — Dashboard, Questionnaire,
  Health record, Files, Wearables

Chosen explicitly (over a single-surface or design-system-only start)
per the user's answer: one combined spec covering everything, so every
surface shares one visual language from the outset rather than the
public site and portals drifting into two different-feeling products
during a staged rollout.

## Direction, per the user's explicit choices

- **Brand**: keep the current palette and identity (the rose/pink
  `--rail-top`/`--rail-bottom`/`--rail-indicator` gradient, the
  "Clinic" wordmark and `Sprig` botanical mark, the warm cream
  `--bg`/`--panel` surface tones) — modernize *execution*
  (spacing, typography, motion, component polish, information
  density, interaction feedback), not identity. No new palette, no
  rebrand.
- **Interactivity priorities** (in addition to what already exists —
  drag-and-drop, the "⋮" menus, the force-directed Graph view,
  folder-tree navigation): micro-animations/transitions, onboarding/
  guided flows for new users, and a command palette / keyboard-first
  navigation layer for power users (admins, practitioners).

## What this is not

- Not a rebrand — no new logo, no new color direction, no new product
  name.
- Not a rewrite of any backend route, data model, or business logic —
  every change here is presentation-layer (`*.svelte`, `app.css`,
  component structure) and new client-side interaction code (command
  palette, onboarding state). No API contract changes are anticipated;
  if a specific page redesign turns out to need one, that gets called
  out explicitly in that page's own spec file, not assumed here.
- Not a single giant PR — see `07-implementation-phasing.md` for how
  this ships incrementally, each phase independently reviewable and
  deployable, matching how every other spec in this repo has shipped.

## Document map

- `01-design-system.md` — the shared foundation every surface draws
  from: refined type scale, spacing, elevation, motion/transition
  tokens, and the component-pattern library (buttons, inputs, cards,
  dialogs, menus, tables, nav) that replaces today's largely
  per-page, copy-pasted CSS.
- `02-public-site.md` — landing page and the rest of the public
  surface.
- `03-admin-portal.md`
- `04-practitioner-portal.md`
- `05-client-portal.md`
- `06-interactivity.md` — micro-animations/transitions, onboarding/
  guided flows, command palette — cross-cutting, applies to all three
  portals (and selectively to the public site).
- `07-implementation-phasing.md` — the shipping plan: what order,
  how each phase is scoped to stay reviewable, and how visual
  regressions get caught before merge.
