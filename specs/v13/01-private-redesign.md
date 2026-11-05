# 01 · Private-route redesign

Scope: `(admin)`, `(practitioner)`, `(client)`. Public routes untouched.
Supersedes the token-only repaint in [v12](../v12/01-dashboard-repaint.md),
which the owner judged too timid ("don't repaint, redesign"). Same
`html[data-surface='app']` scoping and per-portal accents are kept.

## Hard requirements (from the owner)

1. **Falling leaves stay on the app rail.** v12 removed them; they come back
   (`LeafField`, tinted by the portal accent, behind nav content).
2. Redesign the whole private area — shell, headers, home pages, shared
   components, every page via shared classes.
3. **Library keeps 100% of its functionality** — folders, drag-and-drop, icon /
   list / column views, inspector, ingest, staged queue, graph, bulk privacy,
   search. Its `<script>` and event wiring are not touched; only layout/markup
   styling changes.

## Design

**Shell — "floating canvas".** The dark rail now runs the full height and the
page content sits on it as a large rounded sheet with a small inset margin
(Arc / Linear style) instead of a hard vertical split. Mobile: no inset, bottom
bar as before.

**Rail.** 15rem, deep slate with an accent-tinted radial glow at the top-left,
animated leaves (12, brightened so they read on the dark background), brand
lockup, ⌘K search, nav items where the active one gets an accent-tinted gradient
fill, a 1px inner ring and a small accent bar on the left edge, and a user card
(avatar initials + name + sign-out icon) at the bottom. Leaves are hidden under
`prefers-reduced-motion` and in the mobile bottom bar.

**Page header.** A 2.75rem gradient icon tile (portal accent) with a soft
shadow, 1.5rem title, subtitle; sticky, with a frosted sheet background
(`backdrop-filter: blur(14px)`) and a faint bottom hairline.

**Home pages.** A new `PageHero` component (accent gradient, sprig watermark,
eyebrow, greeting, subtitle, optional key-number chips, action buttons).
- Practitioner: "Welcome back, {first name}", Clients/Consults chips, actions
  Start a consult / Add a client / Edit questionnaires (Pro) or Open profile
  (non-Pro). These replace the former "Quick actions" block; no link was lost.
- Admin: "Platform overview", Pending/Approved chips, actions Add resources /
  Review practitioners / Edit questionnaires (also replacing "Quick actions").
- Client: "Hello, {first name}", a Done n/m chip, above the existing care stream.
Below the hero: stat cards (practitioner/admin) and card-style content blocks.

**Components.** Stat tiles with large figures and tinted icon wells; pill chips;
segmented tabs (grey track, raised active segment); rounded tables with hover
rows; dialogs; boxed inputs with an accent focus ring — including bare
text/search/select/textarea controls inside `.detail-pane`, not only
`TextField`; solid buttons with a gradient primary.

**Library.** Toolbar becomes a floating bar (segmented view switch, pill search,
icon actions); folders render as tinted cards with a label, files as clean doc
tiles; list view gets rounded rows; the inspector becomes a raised side panel
with rounded corners and boxed fields; sidebar tree becomes soft nav items.
Folders use the portal accent (not the old Finder blue). Below 960px the
sidebar/inspector stack full-width.

## Implementation notes

- Styles live in `web/src/lib/surface.css` (scoped to `html[data-surface='app']`),
  `Rail.svelte`, and the new `PageHero.svelte`; the three home pages were edited.
- The shell inset uses `overflow: clip` (not `hidden`) so sticky headers work.
- Page roots are forced to `flex: 1` inside the shell (Consult previously did not
  fill the width once the rail color showed through).
- Library overrides are plain global selectors with higher specificity than the
  page's scoped CSS; its `<script>` and markup are unchanged.

## Non-goals

No routing, API, copy, or data-behavior changes; no dark mode; no new
dependencies.

## Acceptance

- `npm run check` 0 errors; `npm run build` OK.
- Leaves animate in the rail on all three portals (not under
  `prefers-reduced-motion`).
- Public routes render identically.
- Library: all view modes render and the same controls remain present.

## Verification status

Checked with a mocked API (screenshots): the three home pages, Library icon view
with inspector, Users, Questionnaires, Consult, mobile bottom bar. **Not yet
verified:** the real backend; Library drag-and-drop, list/column views and the
ingest flow (styled only, logic untouched); Knowledge, Settings, Audit,
Profile, Clients detail and the other client pages.
