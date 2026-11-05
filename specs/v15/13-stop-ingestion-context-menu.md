# Specification 13: Stop Ingestion & Remove File Context Menu

## 1. Overview
During document ingestion, administrators require the ability to halt active processing and optionally remove the file from the intake queue. Prior to this spec, staged ingestion ran asynchronously in the background with no mechanism to abort in-flight LLM calls or cancel queued jobs, and right-clicking an ingesting card only triggered the container empty context menu.

This spec introduces:
1. **Right-Click Context Menu for Ingesting Items**: Right-clicking any ingesting or staged item in the Library (Icon or List view) opens a context menu with options to stop ingesting and remove the file.
2. **Immediate Pipeline Abort**: When an ingestion job is stopped or cancelled, the backend marks the job as `error` ("Ingestion stopped by user") and signals the worker thread to abort promptly across all major pipeline phases (chunking, embedding, knowledge-graph extraction, and Neo4j write) without wasting LLM tokens or compute.
3. **Queue Eviction**: If a stopped job is waiting in `asyncio.Queue` for a concurrency worker slot, the worker skips it immediately upon dequeue.
4. **File Removal**: Selecting "Stop ingesting and remove file" or "Remove file" halts any active ingestion job, deletes the staged item from `staged_sources`, and removes the original file from disk (`originals.delete`).
5. **Direct Action Controls**: In addition to the right-click context menu, cards and table rows surface quick-action buttons (`Stop`, `Retry`, `Remove`) for convenience and mobile touch accessibility.

## 2. API Endpoints
- `POST /api/staged/{staged_id}/stop`: Halts running or queued ingestion jobs for the given staged item.
- `DELETE /api/staged/{staged_id}`: Stops active jobs and permanently deletes the staged source and stored file.
- `POST /api/me/knowledge/stage/{staged_id}/stop`: Practitioner knowledge base counterpart.
- `DELETE /api/me/knowledge/stage/{staged_id}`: Practitioner knowledge base counterpart.

## 3. Frontend Integration
- File: `web/src/routes/(admin)/admin/library/+page.svelte`
- `onStagedContextMenu(e, item)`: Opens `ContextMenu` with `menu.kind === 'staged'`.
- Running job actions:
  - `Stop ingesting`: Calls `POST /api/staged/${id}/stop`, clears client poll timer, updates UI state.
  - `Stop ingesting and remove file`: Calls `DELETE /api/staged/${id}`, purges job and staged record, clears target folder/tag queues.
- Errored/Stopped job actions:
  - `Retry ingestion`: Re-triggers `POST /api/staged/${id}/ingest`.
  - `Remove file`: Discards the file.
- View visibility helper `isStagedVisible`: Ensures in-flight uploads appear inside their target folder or category during ingestion.

