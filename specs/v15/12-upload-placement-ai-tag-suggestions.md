# 12. Upload Placement & Organization: AI Tag Suggestions & Assignment

## Context & Requirement
The user requested:
> "I need, when uploading a document, aside from deciding where the document will live, user should decide which tags it should belong to, give suggestions by AI"

Previously, the post-ingestion placement dialog (introduced in `specs/v15/05`) focused strictly on destination folders (`folder_path`). Ingested documents were tagged by the AI Reader in the background with `topics`, but users could not review, modify, accept, or reject those tags upon intake without opening each document's detail inspector after the fact.

## Architecture & Implementation

### 1. Unified Placement & Tag Confirmation
- Extended `PendingPlacement` in `web/src/routes/(admin)/admin/library/+page.svelte` to include:
  - `suggestedTags: string[]`: AI-extracted topics from the Reader model pass and any intake category context.
  - `selectedTags: string[]`: The active set of tags the user decides to assign. Pre-populated with AI suggestions by default.
  - `newTagInput: string`: Custom tag creation text input.

### 2. Interactive AI Tag Suggestions UI
In each `.placement-card` of the confirmation dialog:
- **Selected Tags Editor**:
  - Displays currently selected tags as interactive chips (`.placement-tag-chip`) with tag icons and an instant delete button (`×`).
  - An inline text input (`.placement-tag-input`) with an associated `<datalist>` of all known library categories/tags (`allKnownTags`) allows typing new tags or picking from existing library tags with `Enter` or the inline `+` button.
- **AI Suggested Chips**:
  - Rendered under an accented `.ai-badge` with a sparkles icon.
  - Each AI suggested tag is an interactive toggle button (`.ai-suggest-chip`).
  - Active suggestions display a checkmark (`✓`) with an active purple background.
  - If a user removes an AI suggested tag, it transitions to an unselected chip with a plus icon (`+`), enabling one-click re-addition at any time.

### 3. Intake Context & Ingestion Queueing
- When uploading documents while inside a category view (`mainTab === 'tags'` and `currentTag`), that category is queued in `pendingTargetTags` and surfaced as a pre-selected destination category.
- When ingestion jobs complete, the Reader's AI topics and target tags are combined, deduplicated, and presented in the confirmation dialog.

### 4. Single & Bulk Confirmation
- **Single Item Confirmation (`confirmSinglePlacement`)**:
  - Updates destination folder: `PATCH /api/sources/{id}/folder`.
  - Updates confirmed tags: `PATCH /api/sources/{id}/topics`.
- **Bulk Confirmation (`confirmAllPlacements`)**:
  - Iterates over all pending items, applying both folder and tag selections in parallel.

## Verification
- `npm --prefix web run check`: 0 errors.
- `npm --prefix web run build`: Built static site successfully.
- `pytest tests/`: All 11 tests passed.

