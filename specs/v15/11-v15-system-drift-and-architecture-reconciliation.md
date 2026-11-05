# 11. v15 System Drift and Architecture Reconciliation

## Why This Exists

This specification records the architectural, behavioral, and operational drift between what earlier specifications (v6.4 through v14) documented versus what the application actually runs following the v15 series of enhancements.

In rapid feature iterations, code evolves to satisfy immediate clinical and operational demands. This document formalizes and reconciles that drift across six core subsystems so future specifications do not build on outdated assumptions.

---

## 1. Library Studio & Dual-Window Organization Drift

### What Prior Specs Assumed (v6.8, v6.11, v8, v13)
- The admin Library was a standard tabbed page (Tabs: *Library*, *Tree*, *Graph*).
- Documents rendered in static card grids, simple list tables, or a read-only folder tree.
- Tags (`topics`) were treated as flat metadata pills editable only inside an inline document form.
- The inspector panel was a permanently reserved right-hand or inline section.

### What the Code Actually Runs (v15/08, v15/10)
- **Studio Chrome & Layout**:
  - The Library has been radically remodeled into a macOS Finder-inspired studio window environment (`.finder`, `.finder-toolbar`, `.pathbar`, `.finder-content`).
  - The Inspector (`.inspector`) is fully dynamic: it stays hidden until a document is selected, and can be dismissed at any time without layout jump.
- **Dual-Window Organization (`Folders` vs `Tags & Categories`)**:
  - A 3-mode segmented switcher (`.window-switcher`) toggle between **Folders** (`mainTab = 'library'`), **Tags & Categories** (`mainTab = 'tags'`), and **Graph** (`mainTab = 'graph'`).
  - Both windows operate on the exact same underlying document corpus (`data.sources`).
  - In `tags` mode, folders represent topics/categories. Slashes in topic strings (`clinical/cardiology`) automatically form nested category folders in the tree, list, icon, and Miller column views.
  - Untagged documents are aggregated in an `(Untagged)` (`__untagged__`) virtual folder, guaranteeing complete discoverability.
- **Drag-and-Drop Categorization**:
  - Internal document cards dragged onto category folders or breadcrumb crumbs immediately update `topics` via `PATCH /api/sources/{id}/topics`.
  - External OS files dropped onto category targets auto-tag newly ingested sources upon completion.

---

## 2. Ingestion Pipeline & File Placement Drift

### What Prior Specs Assumed (v6.8, v6.12)
- Ingestion accepted a single file at a time or scraped a single URL.
- Once staged, files either sat in a separate review tab or auto-ingested silently into the library root folder.
- Placement into subfolders required navigating to the document after ingestion and manually typing a folder path in an input field.

### What the Code Actually Runs (v15/01, v15/03, v15/05)
- **Multi-File Batch Uploads**:
  - Both the "Add resources" modal dialog and direct external drag-and-drop accept multiple files simultaneously.
  - Batch progress tracking surfaces the currently uploading file index and byte transfer rate.
- **Direct OS Drag-and-Drop Ingestion**:
  - Files can be dragged directly from the operating system desktop or file manager into:
    1. Sidebar folder/tag tree nodes.
    2. Main content area (icon grid / list table).
    3. Pathbar breadcrumb segments.
- **Post-Ingestion Placement Dialog**:
  - A dedicated confirmation dialog intercepts completed ingestion jobs.
  - If additional files finish while the dialog is open, they dynamically append to the queue.
  - Suggests target folders based on intake context and existing folders, suppressing raw text inputs unless an admin explicitly clicks "+ New folder".
  - Includes a persistent toolbar notification bell (`.tb-placement-notify`) with a live counter for unattended or dismissed placement reviews.

---

## 3. Concept Graph Physics, Sizing & Navigation Drift

### What Prior Specs Assumed (v6.13, v6.18, v8)
- The concept graph was a standard d3-force network bounded to 80-150 nodes.
- Disconnected graphs clustered tightly in the center, causing overlapping and clutter.
- All nodes were rendered with uniform default radiuses.
- Viewport navigation was restricted to pan/zoom buttons without bird's-eye context.

### What the Code Actually Runs (v15/02, v15/04, v15/06)
- **Connected Component Spatial Separation**:
  - Connected components are partitioned using BFS graph traversal.
  - Disconnected graphs are spaced along an offset force center layout, eliminating center clutter.
- **100% Increased Spacing & Click Blooming**:
  - Base simulation distance between nodes is doubled (+100%).
  - Clicking a node triggers radial blooming, separating its immediate neighbors outward for clear legibility.
- **Data-Volume-Driven Node Sizing**:
  - Default base node size is reduced by 60% (from 8-12px down to ~3.5-5px).
  - Nodes scale dynamically based on relationship degree and passage count ($R \propto \sqrt{\text{degree}}$).
- **Interactive Context Map (Minimap)**:
  - An interactive canvas minimap in the lower-right corner displays the entire graph topology.
  - Features an active viewport rectangle and supports click-to-pan repositioning.
- **Closest-Neighbor Glowing Highlight**:
  - Hovering a concept node isolates and highlights only directly connected neighbor nodes with an accented halo filter.

---

## 4. Mobile Shell & Viewport Container Drift

### What Prior Specs Assumed (v8, v12, v13)
- The application shell assumed desktop monitors with fixed left-hand rail navigation (`AppRail.svelte`).
- Inner pages were rendered in standard container divs without dedicated mobile controls.
- Mobile viewports suffered from horizontal overflow, unreachable nav items, and awkward dual scrollbars.

### What the Code Actually Runs (v15/07, v15/08)
- **Adaptive Mobile Navigation**:
  - Top app bar includes a mobile burger menu trigger (`.burger-btn`).
  - A slide-over side drawer (`.mobile-drawer`) presents the full role-specific navigation menu.
  - A fixed bottom navigation bar (`.mobile-bottom-bar`) provides immediate thumb-reach shortcuts to top tasks (Home, Consult, Library, Clients, Record).
- **Isolated Shell Scrolling (`.portal-main`)**:
  - Outer `body`/`html` scrolling is locked; scrolling occurs exclusively within `.portal-main` with `scrollbar-gutter: stable`.
  - Content containers use fluid CSS grid and flex structures with responsive breakpoints at 960px and 760px.

---

## 5. Practitioner Consultation Workflow Drift

### What Prior Specs Assumed (v6.4, v6.5)
- Practitioner consult sessions started as blank chat threads awaiting user prompt input.
- Reviewing patient context required navigating back to `/practitioner/clients/[id]` or querying the AI manually.
- Consult history only recorded practitioner-prompted Q&A turns.

### What the Code Actually Runs (v15/09)
- **Automatic Opening AI Patient Summary**:
  - Upon initiating or opening a consult session, the system automatically triggers an opening AI clinical briefing.
  - The briefing synthesizes the patient profile, intake questionnaire, recorded labs/conditions/medications, and historical consult notes strictly up to the consultation point in time.
  - Markdown-rendered with clinical sections (`Known Conditions`, `Key Lab Trends`, `Past Consult Highlights`, `Considerations`).
  - Saved into `Session.summary` and seamlessly restored when revisiting past sessions.

---

## 6. Specification Index & Changelog Drift

### What Was Missing
- `specs/README.md` version index halted at `v14`.
- `specs/CHANGELOG.md` had no entries for v15.

### Reconciliation
- `specs/README.md` updated to index `v15` as **implemented** across all 11 specifications.
- `specs/CHANGELOG.md` updated to document the complete v15 release package.

---

## Summary Matrix

| Subsystem | v6–v14 Baseline | v15 Actual Reality |
|---|---|---|
| **Library Organization** | Single folder tree & flat tag pills | Dual-mode: Folders vs Tags/Categories window, hierarchical slash tags, untagged bucket |
| **Library UI** | Card grid / static table | macOS Finder-inspired studio, dynamic collapsible inspector, 3-mode switcher |
| **Ingestion** | Single file, manual post-ingest edit | Multi-file form + OS drag-and-drop to tree/breadcrumbs, smart placement dialog + bell |
| **Concept Graph** | Clustered 150-node D3 graph | Multi-graph separation, 100% spacing, data-volume node sizing, minimap, neighbor glow |
| **App Shell** | Desktop-only rail | Adaptive mobile bottom bar, burger drawer, isolated viewport scrolling |
| **Consultation** | Blank chat start | Automatic opening AI patient history briefing at session launch |
