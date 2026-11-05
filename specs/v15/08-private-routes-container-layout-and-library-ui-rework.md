# Private Routes Container Layout & Library UI Radical Redesign

## 1. Overview
Radical redesign of the container layout, surface CSS, and UI architecture for all authenticated private routes (Admin, Practitioner, and Client portals), paired with a visual and ergonomic overhaul of the Knowledge Library interface while strictly preserving 100% of existing functional behaviors.

## 2. Private Route Container Architecture (`app.css`)
- **Atmospheric Canvas & Ambient Mesh**:
  - Replaced flat single-color portal sheets with dynamic ambient radial mesh lighting tailored per portal:
    - **Admin (`portal-admin`)**: Soft indigo-slate ambient illumination (`radial-gradient(circle at 10% 8%, rgba(99, 102, 241, 0.09) 0%, transparent 45%)`).
    - **Practitioner (`portal-practitioner`)**: Soft teal-mint ambient illumination (`radial-gradient(circle at 10% 8%, rgba(13, 148, 136, 0.08) 0%, transparent 45%)`).
    - **Client (`portal-client`)**: Warm rose-magenta ambient illumination (`radial-gradient(circle at 10% 8%, rgba(217, 70, 239, 0.08) 0%, transparent 45%)`).
- **Floating Studio Island Shell (`.portal-main`)**:
  - Container-query enabled layout (`container: portal-main / inline-size`) for fluid component adaptations.
  - Generous floating radius (`24px` on desktop) with a crisp perimeter highlight border (`--portal-surface-border`).
  - Multi-tier elevation shadow (`0 0 0 1px rgba(255, 255, 255, 0.6) inset, 0 16px 40px -8px rgba(16, 24, 40, 0.08), 0 32px 70px -16px rgba(16, 24, 40, 0.12)`).
- **Frosted Floating Header (`.detail-head`)**:
  - High-performance glassmorphism (`backdrop-filter: blur(20px) saturate(180%)`).
  - Beveled gradient icon emblem with 3D shadow and glow (`.head-ico`).
  - Tight headline typography (`letter-spacing: -0.03em`) and structured subtitle hierarchy.
- **Split-Pane Ergonomics (`.pane-row`, `.list-pane`, `.detail-pane`)**:
  - Translucent list pane with `scrollbar-gutter: stable`.
  - Tactile card list rows with subtle left-border indicator bar (`::before`) on active selection.

## 3. Library UI Radical Redesign (`admin/library`)
- **Command Studio Header (`.finder-toolbar`)**:
  - Frosted glass command bar with elevated back button (`.back-nav-btn`), glowing icon emblem, and responsive title layout.
  - Modern segmented pill view toggle (`.tb-view-toggle`) with smooth active indicator and tactile button feedback.
  - Sleek search capsule (`.tb-search`) with focus ring glow, live spinner, and clear action.
  - Radiant Concept Graph toggle orb button with active gradient pill state.
  - High-visibility notification pill (`Placement needed`) with pulsing beacon.
- **Interactive Breadcrumb Ribbon (`.pathbar`)**:
  - Floating pill-shaped path segments with subtle folder icons, chevrons, and active drag-and-drop destination ring halos.
- **Live Activity & Selection Bar (`.status-row`)**:
  - Frosted action tray displaying active queue counts, live ingestion progress, retry failed action, and bulk selection controls (Make Private, Make Public, Clear).
- **Workspace Explorer Sidebar (`.finder-sidebar`)**:
  - Frosted glass navigation pane (`15rem` width) with root Library counter pill, smooth collapse toggle, and animated dashed external drop overlay.
- **Modern Studio Resource Cards (`.icon-grid`)**:
  - **Folder Cards (`.folder-tile`)**: Capsule cards with colored folder artwork, item count badges, drop-target halo, and double-click navigation.
  - **Document Cards (`.doc-tile`)**: Modern resource cards with file-type extension tag (`PDF`, `MD`, `CSV`, `TXT`), privacy lock badge, placement bell, title with 2-line clamp, hover lift (`transform: translateY(-3px)`), and active selection halo.
  - **Staged / In-Queue Cards (`.staged-tile`)**: Progress cards with animated gradient shimmer bars and live percentage text.
- **Studio Data Table (`.finder-table`)**:
  - Sticky frosted header with uppercase tracking, smooth row hover highlights, and aligned checkbox selection.
- **Miller Columns Browser (`.column-view`)**:
  - Frosted column dividers, active item ribbons, and smooth horizontal scroll.
- **Context Studio Inspector (`.inspector`)**:
  - Sleek floating drawer (`22rem` width) with frosted glass surface, document title, author metadata, quick action buttons, responsive metadata fields, and pill tag cloud.
