# Specification 14: Mouse Block Multi-Select & Batch Context Menu

## 1. Overview
Administrators managing large document collections in the Library and Tags/Categories views require a fluid, desktop-grade way to select multiple items simultaneously using marquee selection (holding the left mouse button and dragging across items) and performing batch actions via context menu.

This spec implements:
1. **Mouse Block (Marquee / Rubber-Band) Selection**:
   - Holding the left mouse button on whitespace in the Library or Tags & Categories window initiates a visual selection rectangle (`.marquee-selection-box`).
   - Every document intersecting the selection box is dynamically added to the selection set (`librarySelected`).
   - Holding `Shift`, `Cmd` (macOS), or `Ctrl` (Windows/Linux) preserves and toggles onto prior selections.
   - Releasing the mouse button finalizes the selection. A plain click outside deselects all items.
2. **Visual Selection States**:
   - Icon View: Selected tiles render with accent rings, soft accent background, and active checkbox pills (`.tile-select-check`).
   - List View: Selected table rows highlight with soft accent backgrounds and synced checkboxes.
   - Columns View: Document rows highlight with active selection tokens.
3. **Multi-Select Right-Click Context Menu (`kind: 'bulk-doc'`)**:
   - Right-clicking any selected item or empty area while items are selected opens a dedicated batch context menu displaying the total selected count.
   - Options include:
     - **Move {N} items to folder…**: Opens bulk destination folder picker with quick suggestions.
     - **Assign category to {N} items…**: Opens bulk tag assignment modal with known category datalist suggestions.
     - **Remove from "{category}"**: (When browsing a specific category) Bulk-strips the active category tag.
     - **Make private ({N})** / **Make public ({N})**: Bulk-toggles privacy on all selected documents.
     - **Remove {N} items from library**: Bulk removal confirmation dialog and deletion.
     - **Clear selection**: Dismisses the selection set.
4. **Synchronized Status Bar**:
   - When items are selected, the top status row surfaces quick action buttons for Move, Category, Make Private/Public, Remove, and Deselect.
