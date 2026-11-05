# Specification 17: Folder & Category Multi-Select in Library and Tags Explorer

## 1. Overview
Extends multi-selection across the Library and Tags/Categories views so that folders and category tags can be multi-selected alongside or independently of documents. This empowers administrators to organize, move, privatize, and delete multiple folders and categories simultaneously via marquee rubber-band drag, Shift/Cmd/Ctrl click toggles, top status bar quick actions, and the floating context menu.

## 2. Core Capabilities
1. **Unified Multi-Selection State**:
   - `selectedFolderPaths`: Set of selected folder paths (e.g. `Set<string>`).
   - `selectedTagPaths`: Set of selected category tag paths (e.g. `Set<string>`).
   - `librarySelected`: Set of selected document source IDs (e.g. `Set<string>`).
   - `totalSelectedCount`: Reactive derived count sum of folders, tags, and documents.
   - `clearAllSelections()`: Atomically resets all three selection sets.

2. **Marquee (Rubber-Band Drag) Selection**:
   - Marquee drag over whitespace calculates 2D bounding-box intersection against all items:
     - `[data-doc-id]` for documents.
     - `[data-folder-path]` for folders.
     - `[data-tag-path]` for categories.
   - Dynamic real-time selection updates all sets simultaneously as the user drags.
   - Holding `Shift`, `Cmd` (macOS), or `Ctrl` (Windows/Linux) performs additive/toggle multi-selection.

3. **Visual Selection Indicators**:
   - **Icon View**:
     - Folders and Categories render `.tile-header-bar` with `DIR` or `TAG` badges and hover/active selection checkboxes.
     - Active selection displays accent glow, soft background, and checkmark.
   - **List View**:
     - Folder and Tag table rows render checkboxes in the first column and highlight on selection.
   - **Column View**:
     - Folder and Tag column buttons display active selection highlighting when multi-selected (`.col-row.selected`).
     - Modifier-click (Shift/Cmd/Ctrl) toggles multi-select without navigating; plain click navigates and clears selections.

4. **Unified Batch Actions & Context Menu (`kind: 'bulk'`)**:
   - Right-clicking any selected folder, tag, document, or empty canvas when `totalSelectedCount > 1` opens the unified bulk context menu.
   - Context menu header displays total count and itemized breakdown (e.g., `3 items selected (2 folders, 1 file)`).
   - **Move Items**: Moves both selected documents (`/api/sources/{id}/folder`) and selected folders (`/api/library/folders/rename`).
   - **Privacy Toggles**: Sets privacy for both selected documents and selected folders (`/api/library/folders/privacy`).
   - **Delete Items**: Atomically deletes selected documents (`/api/sources/{id}`), folders (`/api/library/folders/delete`), and category tags (`/api/sources/{id}/topics`).
   - **Clear Selection**: Clears all selected items.

5. **Top Action & Status Bar**:
   - Surfaces selection breakdown `{totalSelectedCount} selected ({folders} folders, {docs} docs)` with action buttons:
     - **Move**
     - **Category** (when documents are selected)
     - **Make Private / Make Public**
     - **Delete**
     - **Deselect all**
