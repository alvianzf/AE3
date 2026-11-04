# v7/03 — Admin portal redesign

Covers `(admin)/admin/*`: Library (`+page.svelte`, Dashboard, Users,
Questionnaires, Audit history), via `AppRail.svelte`'s admin nav items
and `(admin)/admin/+layout.svelte`'s footer status bar.

## Library — the highest-priority page in this portal

Already the most-iterated page in the app (`specs/v6.11`-`v6.19`,
~2000 lines). This redesign's job here is consolidation and polish,
not new features — every capability this week's specs added
(view modes, Tree view, Graph view, the "⋮" menu, the auto-ingest
queue status bar) already exists; what's missing is a single coherent
visual language tying them together, since each shipped as its own
incremental PR with its own page-local CSS.

- **Promote `.doc-card`/`.folder-card`/`.staged-row` to `Card.svelte`**
  (from `01`) — today's three variants share maybe 70% of their CSS by
  eye but are three separate hand-written blocks in one page's
  `<style>`. One shared base component with per-variant slots (a
  header row, a body, a footer) removes the drift risk every future
  tweak to one currently has to be manually mirrored into the other
  two to avoid (a real, already-seen failure mode this week — see
  `v6.16`'s audit finding that Table view fell behind Icons/List).
- **`EmptyState.svelte`** (from `01`) replaces the current bare
  `<p class="hint">Nothing ingested yet...</p>`/`Nothing matches that
  search.`/`This folder is empty.` strings — a first-run admin's very
  first view of this page, before any upload, is one of these empty
  states; it currently looks like a bug (just text, no visual weight)
  rather than a deliberate "start here" moment.
- **Onboarding** (`06`): a first-run guided tour pointing at "+ Add
  resources", the view-mode toggle, and the Graph/Tree tabs — this
  page alone has grown enough surface area (4 tabs, 3 view modes, a
  multi-step placement dialog) that a brand-new admin with zero
  context has a real "where do I even start" problem today.
- **Command palette** (`06`): Cmd+K to jump straight to a document by
  title, jump to a folder, or trigger "+ Add resources" without
  leaving the keyboard — this page's own search box already does part
  of this, but only within the Library tab (a real gap `v6.16`'s audit
  already found: search doesn't work in Tree/Graph tabs).

## Dashboard

Not read in detail this pass. Known from `specs/v6` history: the
system-health footer bar already moved here from a dashboard section
(`v6` batch, 2026-11-03); flagged for its own read-then-spec pass,
focusing on whether the current dashboard actually answers "what
needs my attention right now" at a glance or is still mostly static
stat tiles (`StatTile.svelte`).

## Users, Questionnaires, Audit history

Not read in detail this pass — each gets its own focused spec entry
when scheduled, reading the actual current implementation first
(per `01`'s stated norm) rather than assuming a shape here.

## Nav rail (`AppRail.svelte`)

- The `isActive()` fix (`v6.15`, most-specific-href-wins) stays —
  this redesign is visual/interaction polish on top, not a logic
  change.
- Visual refresh: current icon-rail-with-hover-label pattern is sound
  (collapses to a bottom bar under 720px) — keep the structure, apply
  `01`'s updated spacing/motion tokens to the hover-reveal label
  transition and the active-indicator bar.
- Add the command-palette trigger here (a visible icon in the rail,
  not just a keyboard shortcut — discoverability matters for a feature
  a first-time admin wouldn't otherwise know exists).

## What this does not change

No change to any admin-only backend route, permission check, or data
model — this portal's redesign is entirely `*.svelte`/CSS/new client-
side interaction components (command palette, onboarding state,
skeletons). Command-palette actions that navigate or trigger an
existing action (e.g. "+ Add resources") call the exact same handlers
those buttons already call — no new backend surface.
