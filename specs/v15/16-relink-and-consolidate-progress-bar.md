# Specs v15 / 16 — Relink and Consolidate Live Progress Bar & Background Management

## 1. Problem Statement
Previously, the graph maintenance operations—**Relink unlinked sources** (`POST /api/relink`) and **Consolidate entities** (`POST /api/consolidate`)—operated as black boxes:
1. When an administrator clicked "Run" on either operation in the Library, the dialog immediately vanished.
2. The user was left with zero visual indication on the screen that a maintenance operation was running, how many documents or entities were being processed, or what percentage was completed.
3. For large backlogs, relinking passages or analyzing entity synonym groups can take several seconds to minutes. Without a progress indicator, users were left guessing whether the process succeeded, failed, or stalled.

## 2. Architecture & Implementation

### 2.1 Backend SSE Progress Streaming & State Management (`app/main.py`)
- **Dual-Mode Maintenance Routes**:
  - `POST /api/relink` and `POST /api/consolidate` now accept `?stream=true` (or `Accept: text/event-stream`).
  - When called with streaming enabled, they yield Server-Sent Events (`data: {...}\n\n`) in real time:
    - `start`: Initial event with total workload size.
    - `progress`: Incremental events with `percentage`, `current`, `total`, `step`, and human-readable `detail` (e.g. `Doc 2 of 5: 'Thyroid Protocol' (passage 4/10)`).
    - `done`: Final event with operation results (`linked`, `failed`, `entity.absorbed`, graph stats).
    - `error`: Error event on unhandled exception.
  - When called without streaming, they fall back seamlessly to synchronous JSON execution, preserving backward compatibility.
- **Concurrent Passage Extraction**:
  - In `relink`, passages for each document are extracted concurrently using a bounded thread pool (`ThreadPoolExecutor(max_workers=8)`), streaming passage progress as each chunk finishes.
- **Live State & Cancellation Endpoints**:
  - `GET /api/maintenance/status`: Returns current maintenance state (`active`, `kind`, `status`, `percentage`, `current`, `total`, `step`, `detail`) to allow client reattachment across page reloads.
  - `POST /api/maintenance/stop`: Gracefully requests cancellation of any active maintenance job.

### 2.2 Frontend Progress Bar Integration (`web/src/routes/(admin)/admin/library/+page.svelte`)
- **Pinned Top Maintenance Bar**:
  - Positioned prominently below the Library header actions.
  - Displays:
    - Animated spinning icon (refresh for relink, sparkles for consolidate).
    - Mode badge: `RELINKING GRAPH` or `CONSOLIDATING ENTITIES`.
    - Live descriptive text (e.g. `Doc 2/5: 'Thyroid Protocol' (6/10 passages)`).
    - Animated progress bar track with glowing shimmer fill.
    - Exact percentage counter (`45%`).
    - Action buttons:
      - `Details`: Re-opens the dialog with full metrics.
      - `Stop`: Stops the in-flight task.
      - `×`: Dismiss button when finished or in error state.
  - When complete, transitions to a success green bar showing summary count (e.g. `Finished! Linked 4 source(s).`), auto-dismissing after 5 seconds.
- **Interactive In-Dialog Progress View**:
  - Instead of dismissing the dialog on "Run", the confirmation dialog transitions into a running view displaying the large progress bar, current doc/passage count, percentage, and a helper note: *"You can close this window at any time — progress will remain active in the top bar."*
  - Footer switches to `Stop` and `Run in background`.
- **Automatic Mount Resumption**:
  - On page load (`onMount`), queries `/api/maintenance/status`. If a maintenance task is already active, immediately attaches to it and polls for live updates until completion.

## 3. Verification & Testing
- `tests/test_maintenance_progress.py`:
  - Verified `GET /api/maintenance/status` empty state.
  - Verified `POST /api/relink?stream=true` SSE event stream (`start`, `progress`, `done`).
  - Verified `POST /api/relink` synchronous fallback.
  - Verified `POST /api/consolidate?stream=true` SSE event stream and entity merge absorption.
  - Verified `POST /api/maintenance/stop`.
- Full test suite passed (22 tests passing).
- Frontend TypeScript check (`npm run check`) passed with 0 errors.
- Frontend production build (`npm run build`) succeeded without warnings or errors.
