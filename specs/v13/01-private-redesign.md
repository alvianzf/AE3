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

**Rail.** 15rem, deep slate with an accent-tinted glow at the top, animated
leaves, brand lockup, ⌘K search, nav items with an accent pill + soft glow on the
active item, user card with avatar + sign-out at the bottom.

**Page header.** A large gradient icon tile (portal accent), 1.5rem title,
subtitle, hairline-free; sticky with a frosted sheet background.

**Home pages.** A new `PageHero` banner (accent gradient, sprig watermark,
personal greeting, key numbers, primary actions) above stat cards and
two-column content cards. Client home gets the same hero above its care stream.

**Components.** Stat tiles with large figures and tinted icon wells; pill chips;
segmented tabs; rounded tables with zebra-free hover rows; floating dialogs;
boxed inputs with accent focus ring; flat buttons with gradient primary.

**Library.** Toolbar becomes a floating bar (segmented view switch, pill search,
icon actions); folders render as tinted cards with a label, files as clean doc
tiles; list view gets rounded rows; the inspector becomes a raised side panel
with rounded corners and sectioned fields; sidebar tree becomes soft nav items.

## Non-goals

No routing, API, copy, or data-behavior changes; no dark mode; no new
dependencies.

## Acceptance

- `npm run check` 0 errors; `npm run build` OK.
- Leaves animate in the rail on all three portals (not under
  `prefers-reduced-motion`).
- Public routes render identically.
- Library: all view modes render and the same controls remain present.
