# 10. Library Tag & Category Organization Window

## Context & Requirement
The user requested:
> "I need a separate library window for tags/categorizations, so the folders are tags/categories. Same data, just different organizationing"

In the Admin Library Studio (`/admin/library`), users previously had access to:
1. **Folders mode**: documents organized hierarchically by filesystem/storage folders (`s.folder_path`).
2. **Concept graph mode**: force-directed interactive entity graph.

This specification introduces a dedicated **Tags & Categories organization window / mode** (`mainTab = 'tags'`), allowing administrators to view, navigate, and manage the exact same underlying document corpus organized hierarchically by tags/topics (`s.topics`).

## Architecture & Implementation

### 1. Unified Dataset ("Same data, just different organizationing")
- No data duplication, schema mutation, or secondary collections.
- The window operates over the existing `data.sources` collection.
- Documents carry tags/categories in `s.topics: string[]`.
- Slash-separated topics (e.g. `medical/cardiology`) naturally map to hierarchical category folders in the tree and column views.
- Untagged documents are cleanly accessible via a dedicated `(Untagged)` node (`__untagged__`), ensuring 100% of documents remain discoverable and organizable.

### 2. Segmented Window Switcher
A persistent `.window-switcher` in the Studio Finder toolbar replaces the previous standalone graph toggle:
- **Folders** (`mainTab = 'library'`)
- **Tags & Categories** (`mainTab = 'tags'`)
- **Graph** (`mainTab = 'graph'`)

### 3. Dedicated Category Tree, Views & Breadcrumbs
When in Tags & Categories mode:
- **Header & Pathbar**:
  - Displays category breadcrumbs (e.g. `Categories > medical > cardiology`).
  - Breadcrumbs act as native drag-and-drop targets for tagging documents or external files.
- **Category Sidebar (`FolderTree`)**:
  - Renders `tagTree` with tag icons (`icon="tag"`).
  - Quick-access root for "Categories" and total count of library documents.
  - Category nodes show item count and support renaming and deletion.
- **Finder Views (Icon, List, Columns)**:
  - **Icon View**: Displays subcategories as category folder tiles with purple tag artwork (`.tag-art`), category name, and item counts, alongside categorized documents.
  - **List View**: Displays subcategories as table rows with tag icons and item counts.
  - **Column View**: Displays Miller columns navigating the category hierarchy with `tagColumns`.
- **Navigation & Drilling**:
  - Single-click highlights/inspects.
  - Double-click navigates into subcategories.
  - Up-level navigation via the toolbar back button or pathbar breadcrumbs.

### 4. Drag & Drop Categorization
- **Internal Drag & Drop**: Dragging a document card/tile onto a category folder (in sidebar, icon view, or breadcrumb) automatically appends that category/topic to the document's `topics` via `PATCH /api/sources/{id}/topics`.
- **External OS File Drop**: Dropping files onto a category folder or anywhere into the content area while inside a category queues the files for upload and automatically tags newly ingested documents with the destination category upon completion.
- **Context Menus**:
  - Empty area context menu offers "New category".
  - Right-clicking a category node offers "Open category", "Rename category…", and "Remove category".
  - Right-clicking a document inside a category offers "Remove from [category]".

## Verification & Validation
- `npm --prefix web run check`: 0 errors.
- `npm --prefix web run build`: Successfully built static site.
- `tests/`: 11 passed in pytest.
