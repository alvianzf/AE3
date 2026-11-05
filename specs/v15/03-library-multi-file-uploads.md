# Library Multi-File Uploads: Form Dialog & Direct Drag-and-Drop

## 1. Form Dialog ("Add resources") Multi-File Upload
- **Multiple file selection**: Added `multiple` attribute to `<input id="file" type="file" multiple>` and enabled multi-file drag-and-drop onto the modal dropzone.
- **Selection list**: Displays selected files in an interactive list with filename, file size in KB, and individual remove (`×`) buttons.
- **Batch summary & progress**:
  - Shows total file count and cumulative size (e.g. `5 files selected (12.4 MB total)`).
  - Primary button dynamically adapts: `Upload X files and queue for ingestion`.
  - Sequential chunked staging with per-file progress tracking (`multiUploadProgress`) and destination folder preservation (`pendingTargetFolders`).
  - "Clear all (X)" button to dismiss the whole batch.

## 2. Direct Drag-and-Drop Multi-File Upload
- Supports dragging multiple files simultaneously from the operating system directly onto:
  - The Library content window (`.finder-content`): files are uploaded and queued directly into the currently active folder (`currentPath`).
  - The Tree sidebar (`.finder-sidebar`): files are uploaded and queued into the root Library folder (`''`).
  - Any folder drop target (breadcrumbs, tree nodes in `FolderTree`, icon folder tiles, list view folder rows, and column view folder rows): files are uploaded and queued into that specific target folder.
- Dynamic toast notifications provide real-time batch queuing feedback (e.g. `Queued (1/3) "file.pdf" for ingestion`).
