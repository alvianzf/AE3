# Specs v15 — Responsiveness Bugs, Experience Gaps, and Placement Notification Real-Time Fixes

## 1. Problem Statement & Motivation
Following the introduction of multi-file ingestion placement confirmation (v15/05, v15/12), icon size controls (v15/18), and marquee selection (v15/14, v15/17), users encountered a state desynchronization bug:
- When a document was ingested and the admin dismissed or cancelled folder/tag placement ("Decide later"), the document remained flagged as needing placement (`pendingPlacements` and `needsFinalization`), correctly showing the toolbar notification badge.
- However, if the user subsequently deleted the file (single item delete, bulk delete, or enclosing folder delete), the notification bell and count persisted, failing to prune in real time until an external page navigation or refresh occurred.
- Furthermore, an end-to-end app audit identified several critical responsiveness bugs and experience gaps across viewports:
  1. **Modal Viewport Overflow**: On compact screens or landscape mobile devices, modal dialogs with tall contents (`Dialog.svelte`) lacked max-height viewport boundaries and internal scrolling, pushing action buttons and footers offscreen.
  2. **Library Studio Toolbar Wrapping**: On mobile/tablet widths (< 760px), `.tb-actions` wrapped buttons haphazardly due to `space-between` alignment, and the search input squeezed between controls instead of stacking neatly.
  3. **Window Switcher Width Constraints**: On narrow devices (< 640px), the 3-tab switcher ("Folders", "Tags & Categories", "Graph") suffered text overflow.
  4. **Public Navigation Hamburger Misalignment**: When links were hidden on mobile (< 760px), the hamburger trigger lacked margin-auto alignment, causing it to sit flush next to the brand wordmark instead of pinned to the right edge.
  5. **Client Portal File Upload Wrapping**: In `files/+page.svelte`, the file input and upload action button lacked responsive flex wrapping.
  6. **Practitioner Consult Mobile Stack Overload**: On viewports < 860px, the client roster, history rail, and patient widget stacked vertically with excessive heights before the consultation chat thread, pushing clinical consultation offscreen.
  7. **Placement Modal Individual Dismissal**: In the placement dialog, users had no mechanism to dismiss an individual file's notification without confirming folder/tags or deciding later for all files.

---

## 2. Technical Architecture & Implementation

### 2.1 Placement Notification Real-Time Pruning & Sync
In `web/src/routes/(admin)/admin/library/+page.svelte`:
1. **Immediate Synchronous Dismissal on Deletion**:
   - Single item deletion (`confirmDelete`): Calls `dismissFinalization(s.id)` before `del(fetch, ...)`, instantly clearing the document from `pendingPlacements` and `needsFinalization`.
   - Bulk deletion (`confirmDelete` with `deletingBulk`): Loops through `docIds` and calls `dismissFinalization(id)` for every selected item prior to sending bulk deletion requests.
   - Folder deletion (`confirmDeleteFolder`): Scans `pendingPlacements` and dismisses any item whose `source.folder_path` matches or is a descendant of the deleted folder path.
2. **Reactive Pruning Against Source Dataset**:
   - Updated the `$effect` observing `data.sources`:
     ```ts
     const existingSourceIds = new Set((data.sources ?? []).map((x: any) => x.id));
     if (placementPreview && !existingSourceIds.has(placementPreview.id)) {
         placementPreview = null;
     }
     if (pendingPlacements.length) {
         const valid = pendingPlacements.filter((p) => existingSourceIds.has(p.documentId));
         if (valid.length !== pendingPlacements.length) {
             pendingPlacements = valid;
             if (pendingPlacements.length === 0) {
                 placementDialogOpen = false;
             }
         }
     }
     if (needsFinalization.size) {
         const valid = new Set([...needsFinalization].filter((id) => existingSourceIds.has(id)));
         if (valid.size !== needsFinalization.size) {
             needsFinalization = valid;
         }
     }
     ```
   - Automatically closes `placementDialogOpen` whenever `pendingPlacements` becomes empty.
3. **Individual Placement Card Dismissal**:
   - Added a `btn-dismiss-single` action next to `btn-confirm-single` on every placement card in the modal:
     ```svelte
     <button
         type="button"
         class="btn-dismiss-single"
         onclick={() => dismissFinalization(item.documentId)}
         title="Dismiss placement notification for this file"
     >
         <Icon name="x" size={12} />
         <span>Dismiss</span>
     </button>
     ```

### 2.2 Modal Dialog Viewport Safety (`Dialog.svelte`)
- Enforced flex-column architecture on open dialogs:
  ```css
  dialog {
      border: 1px solid var(--line); border-radius: 16px; padding: 0; width: min(32rem, 92vw);
      max-height: min(90dvh, 90vh);
      box-shadow: 0 20px 60px rgba(0, 0, 0, .2), 0 4px 12px rgba(0, 0, 0, .08);
      background: var(--panel);
      color: var(--ink);
      animation: liftIn .18s var(--ease) both;
  }
  dialog[open] {
      display: flex;
      flex-direction: column;
  }
  .dh { flex: 0 0 auto; ... }
  .db {
      padding: var(--space-5); display: grid; gap: var(--space-4);
      flex: 1 1 auto; overflow-y: auto; overscroll-behavior: contain;
  }
  .df { flex: 0 0 auto; ... }
  ```
- Ensures dialog footers and action buttons remain visible and clickable across all devices.

### 2.3 Cross-Portal Responsiveness & UX Improvements
1. **Library Studio Toolbar & Chrome (`admin/library/+page.svelte`)**:
   - Short/full label duality for the window switcher:
     ```svelte
     <span class="ws-label-full">Tags & Categories</span>
     <span class="ws-label-short">Tags</span>
     ```
     Switched dynamically via `@media (max-width: 640px)`.
   - On screens < 760px:
     - `.finder-toolbar .head-title`: Added `min-width: 0;` and text truncation with ellipsis for headings and paths.
     - `.tb-actions`: Converted from `space-between` to `justify-content: flex-start; gap: .45rem;`.
     - `.tb-search`: Pinned full-width on its own line (`width: 100%; min-width: 100%; order: 10; margin-top: .15rem;`).
     - `.tb-placement-notify`: Retains the bell icon and numeric badge while hiding the verbose text label (`.notify-label { display: none; }`).
   - On screens < 960px:
     - Constrained `.finder-sidebar` to `max-height: 260px;` so documents remain immediately accessible.
     - Docked `.inspector` with top accent border and `max-height: 60vh;`.
2. **Public Site Mobile Navigation (`PublicNav.svelte`)**:
   - Added `margin-left: auto;` to `.hamburger` ensuring right-edge pinning on mobile viewports.
3. **Public Directory Compatibility (`practitioners/+page.svelte`)**:
   - Added standard `line-clamp: 2;` for multi-line bio clamps alongside `-webkit-line-clamp`.
4. **Client Portal File Intake (`client/files/+page.svelte`)**:
   - Made `.uploader-row` flexible with `flex-wrap: wrap` and fluid file input sizing (`flex: 1 1 12rem`).
5. **Practitioner Consult Studio (`practitioner/consult/+page.svelte`)**:
   - On screens < 860px, constrained `.clientlist` and `.historylist` to `max-height: 8.5rem`, expanded chat main to `min-height: 480px; height: 75dvh;`, and enabled composer wrapping.
6. **Shell Cleanliness (`Rail.svelte`)**:
   - Purged debug console logs from drawer navigation handlers.

---

## 3. Verification & Validation
- **TypeScript & Svelte Check**: `npm --prefix web run check` passes with 0 errors.
- **Production Compilation**: `npm --prefix web run build` passes with 0 errors.
- **Backend Test Suite**: `.venv/bin/pytest tests/` passes 22 tests cleanly in 7.88s.
- **Real-Time Notification Verification**: Single deletion, bulk deletion, folder deletion, and individual card dismissal immediately prune the notification counter and dialog.

