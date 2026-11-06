# 19. v15 Late-Cycle System Drift & Architecture Reconciliation

## Why This Exists

Following the mid-cycle reconciliation in [11-v15-system-drift-and-architecture-reconciliation.md](11-v15-system-drift-and-architecture-reconciliation.md), seven additional major capabilities were engineered in rapid succession to address operational and clinical requirements (specs 12 through 18).

This specification formalizes and reconciles the architectural, behavioral, and operational drift between the initial v15 baseline and the live application as it runs today across all late-cycle capabilities.

---

## 1. Ingestion Lifecycle, Cancellation & AI Suggestion Drift

### What the Initial Baseline Assumed (v15/01, v15/05)
- Ingestion jobs, once enqueued, were immutable black-box operations running in the background worker queue until completion or unhandled failure.
- If an administrator accidentally uploaded the wrong document, duplicate file, or excessively large backlog, there was no mechanism to abort the in-flight process or evict it from the queue without restarting the backend process.
- Staged file cleanup was only possible after completion or fatal failure.
- The post-ingestion placement dialog suggested destination folders, but tag categorization relied entirely on manual typing or post-ingestion tagging.

### What the Code Actually Runs (v15/12, v15/13)
- **In-Flight Ingestion Abort & Queue Eviction**:
  - `POST /api/ingestion-jobs/{id}/stop` signals worker threads to halt processing immediately, clears pending chunking/embedding stages, and sets job status to `'cancelled'`.
  - Staged documents can be evicted and deleted in a single step via the right-click context menu (**"Stop ingesting and remove file"**) or direct row action controls.
- **AI-Powered Placement & Tag Suggestions**:
  - During placement review, an LLM pass analyzes document content to extract high-confidence category tag suggestions.
  - Interactive tag pills render in the confirmation dialog, allowing administrators to add, remove, or customize suggested tags before documents enter the library corpus.
  - Autocompletion datalists surface all existing workspace categories to prevent tag fragmentation.

---

## 2. Knowledge Graph Purity & Domain-Mindful Extraction Drift

### What the Initial Baseline Assumed (v6.13, v15/02, v15/06)
- Every ingested document was routed through an identical clinical extraction pipeline using medical entity prompts.
- Marketing brochures, practice policies, intake guidelines, and administrative documents were subjected to clinical entity extraction, causing severe domain pollution (e.g. general business copy being erroneously categorized as `Integrated Medicine` or generating spurious clinical concepts in Neo4j).

### What the Code Actually Runs (v15/15)
- **Domain-Mindful Document Pre-Classification**:
  - Ingestion documents undergo document domain verification prior to concept extraction.
  - Documents identified as administrative, marketing, or general operations are segregated from clinical knowledge extraction pipelines.
  - Administrative sources are automatically classified into non-clinical category tags (e.g. `marketing`, `administrative`, `operations`) and prevented from polluting the clinical concept graph with non-medical entities.
- **Quarantine & Extraction Guardrails**:
  - The Graph Builder strictly enforces clinical domain boundaries, rejecting non-medical entities and relationships from non-clinical sources.

---

## 3. Background Operations Visibility & Streaming Maintenance Drift

### What the Initial Baseline Assumed (v6.13, v6.15)
- Graph maintenance operations (**Relink unlinked sources** and **Consolidate entities**) were invoked as basic asynchronous tasks without real-time client-side feedback.
- Administrators had no insight into percentage completion, current step, or elapsed/remaining time, leading to repeated clicks, duplicate job triggers, and navigation away from uncompleted tasks.

### What the Code Actually Runs (v15/16)
- **Dual-Mode Server-Sent Events (SSE) Streaming**:
  - Endpoints `GET /api/maintenance/stream`, `GET /api/maintenance/status`, and `POST /api/maintenance/stop` broadcast real-time progress metrics (percentage, current entity/source, total items, detailed sub-step label).
- **Persistent Top Progress Banner (`.maintenance-banner`)**:
  - When maintenance runs, a sticky progress banner mounts below the main app header across all Library tabs and windows.
  - The banner persists across page reloads, tab switches, and dialog dismissals, re-attaching to active SSE streams automatically.
- **Interactive Maintenance Dialog**:
  - Opening the maintenance modal displays an animated pulse indicator, granular progress bar, item counters (`X of Y complete`), and explicit **"Stop"** and **"Run in background"** controls.

---

## 4. Canvas Rubber-Band Marquee Multi-Selection Drift

### What the Initial Baseline Assumed (v15/08, v15/10)
- Item selection in the Library was strictly single-item: clicking a document opened it in the Inspector; clicking outside cleared it.
- Selecting multiple items required individual clicks or checkboxes without spatial drag selection.

### What the Code Actually Runs (v15/14, v15/17)
- **2D Canvas Marquee (Rubber-Band Drag) Selection**:
  - Pressing and holding the left mouse button on whitespace in the Library or Tags window draws a dynamic visual selection box (`.marquee-selection-box`).
  - Intersection math calculates overlaps against rendered bounding client rectangles for all item types:
    - Documents (`[data-doc-id]`)
    - Folders (`[data-folder-path]`)
    - Categories (`[data-tag-path]`)
  - Items dynamically toggle their `.selected` visual tokens in real time as the marquee expands or contracts.
  - Holding `Shift`, `Cmd` (macOS), or `Ctrl` (Windows/Linux) preserves and toggles onto existing selections.
- **Unified Multi-Entity State**:
  - Reactive sets `librarySelected` (doc IDs), `selectedFolderPaths` (folder paths), and `selectedTagPaths` (tag paths) coordinate seamlessly under reactive derived `totalSelectedCount`.
  - Atomic `clearAllSelections()` ensures consistent reset behavior across click events, navigation, and view switches.

---

## 5. Multi-Entity Bulk Context Menus & Action Orchestration Drift

### What the Initial Baseline Assumed (v15/01, v15/08)
- Right-click context menus (`kind: 'doc' | 'folder' | 'tag' | 'empty'`) operated on a single targeted item.
- Batch operations were restricted to documents only (`bulk-doc`), ignoring folders and categories.

### What the Code Actually Runs (v15/14, v15/17)
- **Unified Multi-Entity Context Menu (`kind: 'bulk'`)**:
  - Right-clicking any selected folder, category, document, or whitespace when `totalSelectedCount > 1` triggers a dedicated bulk context menu.
  - The menu header renders total counts with an itemized breakdown (e.g. `5 items selected (2 folders, 3 files)`).
- **Cross-Entity Batch Action Handlers**:
  - **Move**: Concurrently moves documents (`/api/sources/{id}/folder`) and renames/moves folder trees (`POST /api/library/folders/rename`).
  - **Privacy**: Concurrently updates privacy flags on documents (`/api/sources/{id}/privacy`) and entire folder hierarchies (`POST /api/library/folders/privacy`).
  - **Delete**: Prompts for confirmation and deletes selected documents, folder hierarchies, and category tags.
  - **Top Status Bar**: An interactive status strip surfaces real-time counts and quick-action buttons (Move, Category, Privacy, Delete, Deselect).

---

## 6. Visual Density & Multi-View Scaling Drift

### What the Initial Baseline Assumed (v15/08, v15/10)
- The Library card grid and list table rendered with hardcoded, fixed dimensions (fixed `10.5rem` minimum tile column width, fixed padding, static 38px icons).
- Administrators managing dense knowledge bases could not adjust visual density without browser-level zooming.

### What the Code Actually Runs (v15/18)
- **3-Tier Density Toggle (Large, Medium, Small)**:
  - **Large (Default)**: 10.5rem columns, 4.25rem art containers, 38px/36px icons, full metadata pills and footer hints.
  - **Medium**: 8.25rem columns, 3.2rem art containers, 30px/28px icons, compact typography.
  - **Small**: 6.25rem columns, 2.35rem art containers, 22px/20px icons, hidden secondary hints to maximize item density matching macOS Finder small icon layout.
- **Dual-Access Sizing Controls**:
  - Segmented toolbar button group with dedicated scaling glyphs (`size-small`, `size-medium`, `size-large`) immediately adjacent to the Grid / List / Columns view switcher.
  - Canvas context menu submenu ("Icon & Folder Size") with checkmark states.
  - Local storage persistence (`admin-library-icon-size`).
- **Synchronized Multi-View Density**:
  - Container `.size-{size}` class cascades to `.finder-table` (List View) and `.col-pane` (Miller Column View), scaling row heights and padding proportionally.
  - Marquee selection bounding-box math dynamically conforms to rendered DOM elements, preserving 100% selection accuracy across all size tiers.

---

## Summary Matrix: Late-Cycle v15 Evolution

| Capability | Initial v15 Baseline (Specs 01–11) | Live Reality (Specs 12–19) |
|---|---|---|
| **Ingestion Pipeline** | Immutable background worker task; manual post-ingest tagging | Mid-flight task abort (`/stop`), instant file purge, AI tag recommendations with interactive pills |
| **Domain Safety** | Single medical extraction prompt for all files; marketing files misclassified as clinical | Domain pre-classification; administrative/marketing files quarantined from clinical Neo4j concept graph |
| **Graph Maintenance** | Blind asynchronous execution without live progress feedback or abort capability | Dual-mode SSE streaming (`/stream`), sticky top progress banner across reloads, in-dialog progress tracking |
| **Selection Model** | Single-item click selection only | 2D rubber-band marquee drag selection with Shift/Cmd/Ctrl modifier support |
| **Multi-Select Scope** | Document-only batch actions | Unified multi-selection over documents, folders, and categories simultaneously |
| **Batch Orchestration** | Document-specific menu options | Unified bulk context menu with itemized counts; unified batch Move, Privacy, and Delete for docs + folders |
| **Visual Density** | Fixed `10.5rem` card grid and static table rows | User-controlled Large / Medium / Small density toggle (toolbar segmented + context menu) across all views |
| **Density Persistence** | Hardcoded layout | Local storage persistence (`admin-library-icon-size`) |
