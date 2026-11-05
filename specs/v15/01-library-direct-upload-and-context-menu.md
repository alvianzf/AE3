# Library External Drag-and-Drop Upload and Tree Context Menu

## 1. Unified Empty Area Context Menu
- Right-clicking any empty area on the Finder sidebar / FolderTree view opens the identical context menu as right-clicking the empty area of the Library content window:
  - **Add resources** (`+ Add resources` — opens the ingest dialog)
  - **New folder** (`New folder` — opens folder creation modal)
- Context menu clicks on folder nodes stop propagation so folder actions (`Open`, `Rename…`, `Privatize`, `Make public`, `Delete folder`) continue to open without triggering the empty container menu.

## 2. Direct External Drag-and-Drop File Upload
- Dropping files directly from the operating system into the Library window (`.finder-content`) automatically uploads and queues them for ingestion into the currently active folder (`currentPath`).
- Dropping files directly onto the Finder sidebar / FolderTree empty area uploads and queues them into the root Library folder (`''`).
- Dropping files directly onto a specific folder target (breadcrumb segment, tree node in `FolderTree`, icon folder tile, list view folder row, or column view folder row) automatically files the ingested document into that specific target folder upon completion.
- Visual drop overlay indicators appear during external file drag over both the tree sidebar and the library window without interfering with pointer events.
- Internal drag-and-drop moving of existing documents and folders remains completely functional.
