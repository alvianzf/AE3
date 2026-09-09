# 05 · Post-launch additions: CI/CD, chunked uploads, staged review queue

Everything in this document was built and deployed on 2026-09-09, after
[04 · Known issues](04-known-issues.md)'s fix pass shipped. Three
unrelated pieces of work, bundled into one doc because they landed the
same day rather than because they're one feature — see
[`specs/CHANGELOG.md`](../CHANGELOG.md)'s `v4.1` entry for the short
version.

## Automatic deploy

Pushing to `main` now deploys automatically via
[`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml) —
full detail lives in [`DEPLOY.md`](../../DEPLOY.md#automatic-deploy-current),
not duplicated here. The short version: a `check` job (Python syntax +
`npm run check`) gates a `deploy` job (build the SvelteKit frontend, sync
`app/` and the build output to the VPS over SSH, reinstall Python deps,
restart `clinic.service`, hit `/api/health`); `check` also runs on a PR
targeting `main` so it can be reviewed before merge, but `deploy` is
explicitly gated to `push` events only (`if: github.event_name ==
'push'`) so a PR branch is never live before it's actually merged.
Working process going forward: a `develop` branch, a PR into `main`,
merge once checks are green.

Auth is a dedicated, restricted ed25519 deploy key (repo secret
`DEPLOY_SSH_KEY`), not a shared password.

## Chunked upload — files up to 200 MB

**The problem this solves isn't really "large files don't fit in a
request" — it's memory.** `clinic.service` caps this process at 500 MB
(`DEPLOY.md`), and Neo4j's JVM already takes most of what's free on the
box. The previous upload path (`raw = await file.read()`) held an entire
file in memory as one `bytes` object before doing anything else with it;
at 200 MB that's a real OOM risk under load, not a theoretical one.

**New `app/uploads.py`**: domain-agnostic chunk staging. A client splits a
file into pieces and PUTs them one at a time; each chunk is streamed
straight onto a staging file on disk in ~1 MB reads/writes, so the process
never holds more than one chunk's worth of the upload in memory regardless
of the chunk size or the file's total size. Not resumable across a server
restart — an orphaned staging file is swept after 24h, on a best-effort
basis triggered by the next upload's `init` call, not a scheduled job.
`upload_id` is UUID4-opaque with no separate per-owner ownership check —
same trust boundary this app already uses for `session_id`/`source_id`/
`client_id` elsewhere, noted as worth revisiting if that ever needs to
hold against a hostile *authenticated* peer, not just an unauthenticated
one.

**Routes** (mirrored under both domains that accept large files):

| | Admin source ingest | Client file upload |
|---|---|---|
| Init | `POST /api/sources/upload/init` | `POST /api/me/files/upload/init` |
| Chunk | `POST /api/sources/upload/{id}/chunk` | `POST /api/me/files/upload/{id}/chunk` |
| Finish (ingest immediately) | `POST /api/sources/upload/{id}/complete` | `POST /api/me/files/upload/{id}/complete` |
| Finish (stage, don't ingest yet) | `POST /api/sources/upload/{id}/stage` | *(not applicable — client files have no staging concept)* |

The legacy single-request routes (`POST /api/sources`, `POST
/api/me/files`) are **unchanged** — still capped at 20 MB, still read the
whole body in one `await file.read()`. They stay for small files and for
API/script callers (`verify.py`, `verify_v2.py`) that expect exactly that
atomic, one-request shape. Chunked upload is additive, not a replacement.

**Frontend**: `web/src/lib/chunkedUpload.ts` — splits a `File` into 4 MiB
pieces (sized to stay under nginx's default `client_body_timeout` even on
a slow connection — see `DEPLOY.md`'s nginx-settings note) and uploads
them sequentially with per-chunk retry (3 attempts) and a progress
callback. The admin ingest form and the client Files page both use it for
every upload now, regardless of size — one code path, always shows
progress, never risks a single giant request.

**Reused rather than duplicated**: `originals.py` and `vault_files.py`
both gained a `save_from_path()` alongside their existing bytes-based
`save()` — a streaming copy for a file that's already on disk after
chunked upload, so archiving it never needs a second in-memory copy on
top of what chunking already avoided buffering.
`knowledge.ingest_source()`'s `original` parameter now accepts a `Path`
as well as `bytes`, dispatching to whichever `save`/`save_from_path`
variant applies.

## Staged sources — upload/paste now, review, ingest all or one at a time

This is [`specs/v3/18-document-ingest-upgrade.md`](../v3/18-document-ingest-upgrade.md)'s
"staged uploads" component — specced back in v3, marked "spec only, not
implemented," and left that way until now. **All three of v3/18's
components are built, in two rounds the same day: staging + the checklist
+ batch/individual promotion first, then drag-and-drop with a preview and
the web scraper added right after** (see "What's still not built" below
for the one thing genuinely deferred, from Component 1).

### Why this needed a real change, not just a UI tweak

Before this, upload and ingest were the same atomic action —
`_ingest_pages()` (the Reader call, chunking, concept extraction, and the
Neo4j write) ran synchronously inside the same request that received the
file. There was no state for "uploaded, not yet decided whether to keep."
An admin who wanted to gather several sources before committing any of
them had no way to do that — every add was immediate and final.

### Data model

New `staged_sources` table in `core.db` (`app/core_store.py`):

```sql
staged_sources (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,          -- 'file' | 'text' | 'scraped_url'
  filename TEXT,
  source_url TEXT,             -- set only for kind='scraped_url'
  media_type TEXT,
  pages_json TEXT NOT NULL,    -- [[page_number|null, text], ...]
  char_count INTEGER NOT NULL,
  page_count INTEGER,
  created_at TEXT NOT NULL,
  created_by TEXT NOT NULL
)
```

`source_url` was added in the second round (migrated — `staged_sources`
already existed in production without it, same `ALTER TABLE` pattern this
file already uses elsewhere).

**One deliberate deviation from v3/18's proposed schema**: that spec's
`staged_sources` had a flat `extracted_text TEXT NOT NULL` column. This
implementation stores `pages_json` — the same `[(page_number, text), ...]`
list shape `_extract_pages()`/`_extract_pages_from_path()` already
produce — instead. A flat string loses page boundaries; a PDF staged now
and promoted later would fall back to "passage 3 of 9"-style citations
instead of "page 4," a real quality regression for exactly the documents
most likely to be staged (long PDFs someone wants to review before
committing). The raw file itself is still archived the same way v3/18
proposed — reusing `originals.py`'s id-keyed `save()`/`save_from_path()`
with the staged item's own id standing in for a source id, since neither
function cares what kind of id it's given.

### Routes (all admin-only, `Depends(auth.require_admin)`)

| Route | Does |
|---|---|
| `POST /api/staged` | Stage a small file (multipart) or pasted text — no Reader call, no Neo4j write |
| `POST /api/sources/upload/{id}/stage` | Same, for a file that came in over chunked upload |
| `POST /api/scrape` | Fetch a URL, strip it, extract via Haiku, stage the result (`kind='scraped_url'`) |
| `GET /api/staged` | List staged items (title/kind/page-count/short preview — not the full text, so the checklist doesn't pull every staged document's body over the wire) |
| `GET /api/staged/{id}/file` | Inline preview for a staged file — same `inline`-for-pdf/text, `nosniff` logic `/api/sources/{id}/original` already uses |
| `DELETE /api/staged/{id}` | Discard without ingesting |
| `POST /api/staged/{id}/ingest` | Promote one staged item through the real pipeline |
| `POST /api/staged/ingest` | Promote several at once (`{ids: [...]}`); a single item's failure (e.g. a duplicate-content 409) is recorded in the response's `failed` list without aborting the rest |

Promotion calls the same `_ingest_pages()` every other ingest path already
uses — Reader, chunking, concept extraction, the Neo4j write — reading
`pages_json` back out instead of re-extracting anything. The staged row
and its archived file are deleted once promotion succeeds.

### The web scraper (v3/18 Component 2)

**New `app/scraper.py`** — `fetch_and_strip(url)`: a blocking `urllib.request`
GET (stdlib only, no new dependency — same "blocking call in a plain
`def` route, FastAPI's threadpool handles it" convention this app already
uses for PDF extraction), then an `html.parser.HTMLParser` subclass that
drops `<script>`/`<style>`/`<nav>`/`<header>`/`<footer>` tags and their
contents. This step exists purely to cut token cost and obvious noise
before the real extraction runs — it does **not** attempt the actual
"discard chrome, keep content" judgment call (a `<div
class="sidebar-links">` styled to look like navigation still reaches the
next step), because a tag-based selector can't make that call correctly;
that's what the LLM step is for.

**New `llm.extract_article(stripped_text, url)`** — a plain-text
completion (not a JSON-schema call like every other role in `app/llm.py`;
closer in shape to `answer()`'s free-text output than `read_source()`'s
structured card, since the output *is* the document body). Uses
`cfg.reader_model` — Haiku by default, a bounded extraction task that
doesn't need a stronger model. System prompt is explicit, matching what
was asked for word for word: extract only the content a human reader came
for, discard navigation/headers/footers/ads/chrome, and — stated twice,
deliberately — never summarize, rephrase, shorten, or otherwise alter the
content kept. Reproduce it verbatim.

**Known, stated gap**: a JavaScript-rendered page (a React/Vue SPA with no
server-rendered content) has no text for `urllib.request` to see at all —
`fetch_and_strip()` 400s with a message saying so rather than silently
returning nothing useful. A headless-browser fetch would fix this but is
a materially heavier dependency; not added.

### Frontend

The admin Knowledge page's "1 · Teach Clinic" panel is now three tabs
(`Tabs.svelte`) instead of one form:

- **Upload a document** — a real drag-and-drop zone (click to browse
  still works), not a bare `<input type="file">`. Once a file is chosen,
  a PDF gets a live native `<embed type="application/pdf">` preview
  before it's even staged — browsers already render PDFs, so this needed
  no new dependency, same reasoning v3/18 gave for the pre-rewrite
  dropzone's preview.
- **Paste text** — unchanged from the single-tab version.
- **Enter URL** — a URL field and a "Scrape and add to staged list"
  button; an indeterminate progress bar plays while the fetch+strip+
  extract round trip is in flight (there's no byte-level progress to
  report for a single request the way chunked upload has).

Staged items render as a checklist below the tabs either way — checkbox,
filename/URL/kind/page-count, a short text preview, a **View**/**Source**
link (file preview or the original URL, depending on kind), and per-row
**Ingest**/**Discard** actions — plus an **Ingest selected** button for
promoting a checked batch at once.

### What's still not built (from v3/18, deliberately out of scope)

- **A PDF thumbnail in the checklist row itself.** v3/18 explicitly
  recommended against N simultaneous native `<embed>` previews for N
  staged rows; the checklist still uses a filename + kind chip + page
  count for already-staged items, with the real preview only shown for
  the *currently selected, not-yet-staged* file in the Upload tab (one
  embed at a time, never N) — matches what v3/18 actually recommended,
  not a shortcut taken here.

## Layout: fixed single-column stacking on multi-panel screens

Flagged directly (a multi-panel admin screen "annoying to look at").
Added a shared `.rail-layout`/`.rail` utility to `web/src/app.css` (a
22rem rail + a 1fr main column, collapsing to one column under 960px)
instead of a bespoke grid per page, and applied it to the three screens
that actually had a wide-main-plus-narrow-secondary shape stacked as two
full-width blocks: the admin Knowledge page, the practitioner Dashboard,
and the practitioner client-detail page. Deliberately left alone:
Profile (two similarly-narrow forms — a wide second column would just be
empty space), `/account` (a deliberately narrow single-purpose page), and
every page that only has one panel to begin with.

## Bug fix: "What Clinic knows" always showed 0

`data.graph.node_count`/`data.graph.edge_count` — read by the admin
Knowledge page's Tier-2 graph-stats line — never existed on `GET
/api/graph`'s real response shape (`concepts`/`mentions`/`order_edges`/
`source_links`/`unlinked`, per `knowledge.graph_stats()`). The panel
always displayed `0 ?? 0` regardless of the graph's real state. The
pre-rewrite `static/app.js` used the correct field names
(`g.concepts`, `g.mentions`); the SvelteKit rewrite introduced the
mismatch, and it wasn't caught by [04](04-known-issues.md)'s review —
found instead when a user asked "why is this still empty" and it turned
out not to be: the real graph, checked directly against the live server,
had 70 concepts, 70 mentions, and 7 cross-source-linked pairs at the
time. Fixed by reading the real field names.
