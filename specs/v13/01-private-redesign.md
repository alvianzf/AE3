# 01 · Private-route redesign

Scope: `(admin)`, `(practitioner)`, `(client)`. Public routes untouched.
Supersedes the token-only repaint in [v12](../v12/01-dashboard-repaint.md).
Adheres strictly to the app's CSS conventions without standalone `surface.css`
overrides.

## Hard requirements (from the owner)

1. **Falling leaves stay on the app rail.** They animate in the rail (`LeafField`,
   tinted by the portal accent, behind nav content).
2. **Follow app CSS conventions:** Design tokens live in `app.css` under `.portal`
   and `.portal-{role}`. Styles are maintained in component `<style>` blocks.
   No separate `html[data-surface]` stylesheet.
3. **Different colors for different roles across the whole portal:**
   - **Admin:** Midnight indigo (`#6366f1` accent, `#0d1026` rail, `#f6f7fb` canvas)
   - **Practitioner:** Nordic teal (`#0d9488` accent, `#071918` rail, `#f4f8f7` canvas)
   - **Client:** Berry rose (`#be185d` accent, `#1c0c16` rail, `#faf6f8` canvas)
4. **Library topbar must be consistent with the rest of the pages.** Replaced the
   divergent toolbar with the unified `.detail-head` structure (gradient icon
   badge, title, subtitle, and right-aligned action cluster).
5. **Library keeps 100% of its functionality** — folders, drag-and-drop, icon /
   list / column views, inspector, ingest, staged queue, graph, bulk privacy,
   search. Its `<script>` logic and event wiring are not touched.
6. **Fix right-click context menu and dialog styling:** Fixed sheet-rule leakage
   that caused 700px vertical stretching on popovers. Context menus and modal
   dialogs are styled cleanly and compactly.

## Design System

**Shell — "floating canvas".** The dark rail runs full height with portal-accent
glow and animated leaves. Page content is enclosed in `.portal-main`, a large
rounded sheet (`border-radius: 20px`, `box-shadow`) inset from the outer edges.
Mobile: bottom bar, full-width canvas.

**Rail (Sidebar).** 15rem, deep slate/role tinted dark base with ambient glow,
animated leaves (12, brightened for readability), brand lockup, ⌘K search,
and active items styled with glowing indicator and accent pill. User profile card
at the bottom with initials avatar and sign-out.

**Page Header (`.detail-head`).** A 2.75rem gradient icon tile (portal accent)
with soft shadow, 1.5rem bold title, subtitle, and right-aligned `.head-actions`.
Sticky with a frosted backdrop blur (`backdrop-filter: blur(16px)`).
Applied uniformly across all pages including Library.

**Home pages.** Clean `.detail-head` headers with personalized greeting and
primary actions, responsive metric stat tiles, and structured content cards:
- **Practitioner:** Overview header with "Start consult" and "Add client" actions,
  checklist banner, 4 StatTiles, Recent Consultations with client avatar, and
  Clinical Tools shortcuts.
- **Admin:** Platform Overview header with "Add resources" and "Review practitioners",
  4 StatTiles, Recent Audit activity, and Latest Uploads.
- **Client:** Your Care header with 3 interactive health record/questionnaire cards
  and wearable integration preview.

**Components.**
- Stat tiles with large figures (`1.6rem`), bold tabular figures, and tinted icon wells.
- Segmented tabs with smooth active pills.
- Rounded data tables with hover rows.
- Context menus (`ContextMenu.svelte`): 12px radius, compact padding, smooth hover states.
- Dialogs (`Dialog.svelte`): 16px radius, dark blur backdrop, header with close icon,
  grey action footer.
- Boxed inputs with 3px focus ring.

**Library.**
- Topbar unified with `.detail-head` (`.finder-toolbar`).
- Segments for view toggle, sort menu, search, graph toggle, and "Add resources".
- Folders and files styled as elevated cards with hover lift.
- Raised inspector panel on selection.

## Implementation notes

- Removed `web/src/lib/surface.css` and `web/src/lib/surface.svelte.ts`.
- Portals wrap their shell in `<div class="app-shell portal portal-{role}">` and
  content in `<main class="portal-main">`.
- This prevents child modals and fixed overlays from inheriting layout margins
  or min-height constraints.

## Acceptance & Verification

- `npm run check` 0 errors; `npm run build` OK.
- Tested and verified with screenshots:
  - Library topbar and right-click context menu
  - Right-click "Move to folder" modal dialog
  - Practitioner, Admin, and Client home pages
  - Mobile bottom navigation
