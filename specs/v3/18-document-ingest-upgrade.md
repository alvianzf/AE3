# 18 · Document ingest upgrade: staged uploads, PDF viewer, web scraper

Requested directly: PDF upload with a drop-zone thumbnail and a persistent
viewer to revisit the document later; a web-page scraper that captures a
URL's content, run through an LLM to discard navigation/header/footer
chrome — explicitly **not** to summarize or alter the content; and an
ingest checklist with a badge distinguishing "already ingested into RAG"
from "saved as a file only." Spec only — no code, no `static/`/`src/`/
`app/` changes.

**Lives in `v3/`, not `v4/`.** This is a backend/data-model feature —
staged uploads, a scraper route, an ingest checklist — independent of
which frontend framework serves it. It applies to the app as it ships
today and would apply just as much after a SvelteKit rewrite; nothing here
depends on `v4`'s open questions.

## The gap this actually requires: upload and ingest are the same action today

`POST /api/sources` (`app/main.py:130`) is atomic: read → Reader LLM call
→ chunk → concept-extract → write to Neo4j, all in one request, with no
intermediate state. There is no Neo4j `Source` node that exists
"uploaded but not yet ingested" — a `Source` node's existence *is* the
definition of ingested (`app/knowledge.py`'s `ingest_source()` is the only
place one gets created). The user's ask — upload/scrape now, pick what to
actually ingest later via a checklist, with a badge for each state — needs
a real staged state that doesn't exist in the current model. This is the
one piece of genuinely new backend work everything else in this document
hangs off of.

**Decision: staged items live outside Neo4j, in a new lightweight store,
until promoted.** Concretely, a new `staged_sources` table — proposed
location: `core.db` (`app/core_store.py`'s existing SQLite database,
already the home for cross-cutting non-vault, non-graph state like
`profile_view_events`/`contact_form_submissions`, per
[02](02-data-model.md)) — not a new database file, reusing the schema
pattern already established there:

```sql
staged_sources (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,               -- 'file' | 'scraped_url'
  filename TEXT,                     -- original filename, or null for a scrape
  source_url TEXT,                   -- the scraped URL, or null for a file upload
  media_type TEXT,                   -- for a file: its content-type
  extracted_text TEXT NOT NULL,      -- PDF-extracted text, or scraper output — what
                                      -- would become `body` on ingest
  page_count INTEGER,
  created_at TEXT NOT NULL,
  created_by TEXT NOT NULL           -- admin id, audit parity with knowledge.log()
)
```

The raw file itself (for a PDF/txt/md upload) is archived the same way
`originals.py` already archives ingested files — reusing that module's
`save()`/`path()` functions with the staged item's `id` in place of a
`source_id`, since the function is already id-keyed and filename-suffix-
aware, not source-specific in any way that would need changing.

**Promotion (the "Ingest" action) is the existing pipeline, unchanged**:
selecting one or more staged items and clicking "Ingest" calls exactly
`add_source`'s existing logic (Reader → chunk → concept-extract →
`knowledge.ingest_source()`) using `staged_sources.extracted_text` as the
body instead of a fresh upload, then deletes the promoted row from
`staged_sources` (and moves its archived file from the staged-files
directory into `originals`' directory under the new `Source` id, or
simpler: originals are always archived under the *staged* id, and
`ingest_source`'s existing `original` archival path is skipped for
promotions — the file's already on disk, just re-pointed to by the new
`Source` node's `original_name`/id). Either is a small, mechanical
decision for whoever implements this; not a design fork worth resolving
here.

## Component 1 — PDF drop-zone, thumbnail, persistent viewer

**The drop-zone already exists.** `static/index.html`'s `#dropzone`
(`Teach Clinic` panel) already supports drag-and-drop and click-to-browse
(`static/app.js:184` `/* Admin 1 · dropzone with preview */`). Nothing new
needed there.

**The "preview" is already a real PDF render, not a placeholder** —
`static/app.js`'s `showPreview()` embeds the chosen file with
`<embed type="application/pdf">` before it's even submitted, with the
comment *"browsers render PDFs natively, so the first page is a real
preview"* (`app.js:200-203`). This is the mechanism to reuse, not replace —
this app has already deliberately avoided a PDF.js dependency and found
the native-embed approach works. Two things are actually new:

1. **A thumbnail in a list of multiple staged items** (the checklist,
   component 3) is a different case from today's single-file preview: a
   native `<embed>` per row would mean N simultaneous PDF plugin instances
   for N staged files, which is real, avoidable browser resource cost —
   this app's own size-consciousness (`specs/v3/15-design-system.md`'s
   "at this project's size" reasoning, used to justify *not* adding a JS
   grid library in `specs/v3/17` X3) argues against it here too.
   **Recommendation: a static icon (PDF glyph) + filename + page count as
   the list-row thumbnail**, with the real native-embed preview rendered
   on demand — clicking a staged row opens the existing `showPreview()`-
   style embed, not N of them rendered eagerly.
2. **Revisiting an already-ingested document's PDF** — `GET
   /api/sources/{id}/original` already exists and already serves with
   `Content-Disposition: inline` for `application/pdf`
   (`app/main.py:337-364`, explicit comment: *"the two types we actually
   want to preview"*) — an `<iframe>`/`<embed src="/api/sources/{id}/original">`
   on the source's detail view (wherever that's surfaced today in
   `static/index.html`'s library list) is a markup-only addition, no new
   route. For a **staged** (not yet ingested) item, the equivalent route
   doesn't exist yet and needs one: `GET /api/staged/{staged_id}/file`,
   same inline-disposition logic, serving from the staged-files directory
   `originals.save()`/`path()` already generalizes to.

## Component 2 — Web scraper: fetch, strip chrome via LLM, do not summarize

**New route: `POST /api/scrape`** (admin-only, `Depends(auth.require_admin)`,
same guard every other library-ingest route already uses). Body: `{url:
str}`. Three steps, each independently checkable:

1. **Fetch.** No HTTP client library exists in this project today
   (`requirements.txt` has no `httpx`/`requests` — confirmed by reading
   it). **Recommendation: stdlib `urllib.request`, not a new dependency**
   — this is a single blocking GET with no need for the connection
   pooling/async-native advantages `httpx` would bring, and the project's
   own convention (`app/main.py`'s `_extract_pages` for PDFs) already
   treats this kind of I/O as a plain synchronous `def` route, letting
   FastAPI's threadpool handle the blocking call exactly like the existing
   PDF-extraction path does — same pattern, zero new dependency. A
   real, honest limitation to flag: `urllib.request` doesn't handle
   JavaScript-rendered pages (a React/Vue SPA with no server-rendered
   content) — if that turns out to matter in practice, the fallback is a
   headless-browser fetch, which *would* be a real new dependency
   (Playwright or similar) and a materially heavier feature; not proposed
   here, flagged as a known gap if a scraped page comes back empty.
2. **Strip HTML markup to visible text, cheaply, before the LLM ever sees
   it** — a stdlib `html.parser.HTMLParser` subclass dropping
   `<script>`/`<style>`/`<nav>`/`<header>`/`<footer>` tags and their
   contents outright, then concatenating remaining text nodes. This isn't
   the "discard nav/headers" step the user asked for — tag-based stripping
   catches semantic `<nav>`/`<header>` elements but not a `<div
   class="sidebar-links">` styled to look like navigation, which is
   exactly the case that needs judgment, not a selector. This step exists
   purely to cut token cost and noise before the real extraction step,
   not to do the extraction itself.
3. **The actual "discard chrome, keep content, don't summarize" step is a
   new LLM call**, not an extension of the Reader
   (`app/llm.py:124`'s `read_source()` takes already-clean `text` as an
   input and produces title/summary/topics/grade metadata — a different
   job, downstream of this one, unchanged). Proposed as a new function,
   e.g. `app/llm.py`'s `extract_article(html_text: str, url: str) -> str`,
   with a system prompt whose entire job is extraction, stated as
   explicitly as the user stated it:

   > You are given the text content of a web page, already stripped of
   > script/style tags. Extract only the main article/content text — the
   > words a human reader came to this page to read. Discard navigation
   > menus, headers, footers, cookie banners, ads, related-article lists,
   > comment sections, and site chrome.
   >
   > Do not summarize, rephrase, shorten, or otherwise alter the content
   > you keep. Reproduce it verbatim, word for word, exactly as it appears
   > in the source. Your only job is deciding what is content and what is
   > chrome — never editing the content itself.

   This is a **plain-text output, not a JSON-schema call** like every
   other `_json_call()` in `app/llm.py` — the other roles all return
   structured fields (grade, topics, verdict); this one's output *is* the
   document body, so a raw-text Claude call (`client.messages.create`
   without a tool/schema) is the right shape, closer to how
   `app/llm.py`'s `answer()` role for the AI team's free-text output
   already works than to `read_source()`'s structured-card shape.
4. **Result becomes a staged item**, same `staged_sources` row shape as
   an uploaded file (component 1's table), `kind='scraped_url'`,
   `source_url` set, `filename` null, no archived file (there's no binary
   to keep — the extracted text *is* the artifact, same as pasted text
   today has no "original" to download).

**Not a new named AI-team role.** `specs/v3/07-ai-team.md` treats
Reader/Indexer/Librarian/Specialist/Checker (plus on-demand
Consolidator/Summariser) as a deliberately bounded, named set — the
version's whole point was resisting scope creep into "a general
agent-to-agent framework." `extract_article()` is a utility LLM call in
the same spirit as `extract_concepts()` (the Indexer's underlying
function, never itself elevated to a capital-letter "role" in the
product's own language) — worth a clear mention in whichever doc
eventually updates `07-ai-team.md`'s pipeline diagram, not a new numbered
role.

## Component 3 — Ingest checklist with status badges

**Lives on the same screen as upload** (`static/index.html`'s `Teach
Clinic` panel), not a separate review page — the existing three-panel
admin knowledge dashboard (`specs/v3/04-admin-portal.md §2`,
[15-design-system.md](15-design-system.md)'s numbered-step framing:
1 Teach Clinic, 2 The library, 3 What Clinic knows) already treats
"add a source" and "see what's in the library" as adjacent panels a
person moves between in one sitting; a staged-items list belongs in panel
1, between the drop-zone/scraper inputs and the existing "Add to library"
button, not a fourth destination.

**UI, concretely:** the drop-zone and a new "Scrape a URL" input both add
rows to a staged-items list (checkboxes, thumbnail per component 1,
filename/URL, an "Ingest selected" button replacing today's single-file
"Add to library" submit). Each row's checkbox defaults checked for the
item just added, unchecked for anything already sitting in the list from
an earlier visit — batching multiple uploads before ingesting all of them
at once is the actual point of "checklist," not a defensive default.

**Badges**: two states, both derivable from where a source's row of data
actually lives, not a new status enum to keep in sync —

- **"Saved as file"** — present in `staged_sources`, no corresponding
  `Source` node yet.
- **"Ingested"** — promoted; the row now only exists as a `Source` node
  (with passages, grade, topics) in Neo4j, `staged_sources` row deleted.

No third state needed (no "ingesting…" — promotion is one FastAPI request,
same synchronous-call shape `add_source` already is; a spinner/disabled-
button during the request covers it, not a persisted state). Both lists
(staged items + already-ingested library items) can render on the same
screen, so an admin sees "what's ready to ingest" and "what's already in"
without navigating away — staged items above the existing library list in
panel 1/2, or a single merged list with the badge as the only visual
differentiator; either is a UI-layer choice for whoever implements this,
not a data-model one.

## New backend work, summarized

- **New table**: `staged_sources` in `core.db` (schema above).
- **New routes** (all admin-only, same guard as every existing
  `/api/sources*` route):
  - `POST /api/staged` — upload a file (multipart, mirrors `add_source`'s
    file-handling branch minus the ingest step) or accept pasted text
    without ingesting.
  - `POST /api/scrape` — the web-scraper flow (component 2).
  - `GET /api/staged` — list staged items, for the checklist.
  - `GET /api/staged/{id}/file` — inline file view (component 1).
  - `DELETE /api/staged/{id}` — discard a staged item without ingesting.
  - `POST /api/staged/ingest` — body `{ids: [...]}`, promotes each
    through the existing `add_source` pipeline, one Reader call per item
    (no batch LLM call — each source gets its own title/grade/topics,
    same as today).
- **New `app/llm.py` function**: `extract_article()` (component 2), a
  plain-text extraction call, not a new named role.
- **New dependency: none required** — stdlib `urllib.request` and
  `html.parser` cover fetch + tag-stripping; the existing `anthropic`
  client covers the extraction call.

## Explicit non-goals

- **JavaScript-rendered page scraping** — flagged as a known gap in
  component 2, not solved here; would need a headless-browser dependency,
  a materially bigger feature.
- **OCR for scanned PDFs** — unchanged, still out of scope
  (`app/main.py:161-164`'s existing 400 error on an unreadable PDF stands).
- **Batch/bulk LLM calls for ingesting multiple staged items at once** —
  each promotion is its own Reader call, same cost/behavior as ingesting
  one at a time today; a batch-summarization-of-many-sources capability is
  a different feature, not requested here.
- **Client-portal file uploads** (`static/client/files.html`,
  `app/main.py`'s `/api/me/files`) — unrelated: that's a client's own
  vault-scoped document storage, no ingest/RAG concept at all, not touched
  by this document.
