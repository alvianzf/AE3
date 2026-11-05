# Ingested Files Placement Confirmation Dialog & Toolbar Notification

## 1. Automatic Ingested File Placement Dialog
- **Trigger**: When an ingestion job finishes (`job.status === 'done'`), the ingested document is added to the pending placement queue (`pendingPlacements`) and the placement confirmation dialog opens automatically.
- **Real-Time Queue Append**: If another ingestion queue finishes while the dialog is already open, the newly finished file is immediately appended to the dialog's reactive list in real time without interrupting the user or resetting existing selections.
- **Smart Destination Suggestions**:
  - Automatically identifies a recommended folder based on intake context:
    1. The destination folder targeted during upload/staging (e.g. dropped on a specific tree folder or breadcrumb).
    2. The Reader's AI-suggested folder (`doc.suggested_folder`).
    3. Document metadata or folder name keyword matching.
    4. Library root (`/ (Library root)`) if no specific subfolder matches.
  - The suggested folder is clearly marked with a `Suggested: /...` badge and pre-selected with `★ Suggested` in the folder dropdown.

## 2. Selection Control (No Text Inputs by Default)
- **Folder Dropdown**:
  - The admin decides the destination folder using a clean `<select>` dropdown populated with all existing library folders (`folderPaths`) and root (`/`).
  - By default, **no text input is rendered anywhere** in the placement dialog.
- **On-Demand New Folder Creation**:
  - Only when the admin explicitly chooses `+ Create new folder…` from the dropdown or clicks the `+ New folder` button does an inline text input appear for that specific file.
  - The text input allows entering a custom folder path (e.g. `Research/Cardio`) with `Enter` to confirm and a `Cancel` button to revert back to existing folder choices.

## 3. Persistent Toolbar Reminder & Re-opening
- **Notification Button**:
  - Positioned in the Library toolbar (`tb-actions`) alongside library actions.
  - Features an active bell icon, pulsating indicator ping, "Placement needed" label, and dynamic count badge indicating how many files are waiting for placement confirmation.
- **Dismiss & Re-Open**:
  - The admin can close the dialog at any time via the `×` button or "Decide later" button.
  - Closing the dialog preserves the pending queue; the notification button remains visible with the reminder badge.
  - Clicking the notification button at any time re-opens the placement dialog with all pending files.

## 4. Confirmation Actions
- **Single File Confirmation**: Inline `Confirm` button moves that individual file to its chosen destination, removes it from the queue, and updates the badge.
- **Batch Confirmation**: `Confirm all (X)` button in the dialog footer applies destinations for all pending files at once and closes the dialog when complete.
