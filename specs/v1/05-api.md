# 05 · HTTP API

JSON over HTTP, FastAPI. Every route except `/gate` and `/api/health` requires the
access cookie ([07](07-security.md)); an unauthenticated `/api/*` call returns
**401**, and an unauthenticated page request returns the gate page.

Scripted clients must send a recognisable `User-Agent` — Cloudflare's browser
integrity check answers **error 1010** to unnamed agents.

---

## Ops

### `GET /api/health`
Open by design, so a monitor can check liveness without holding the door code.

```json
{ "neo4j":     { "ok": true },
  "anthropic": { "ok": true },
  "patients":  { "ok": true },
  "stats": { "sources": 8, "chunks": 10, "topics": 17 } }
```
A failed probe carries `{ "ok": false, "error": "<Type>: <message>" }`.

---

## Library

### `POST /api/sources`
`multipart/form-data`. Ingests a source: read → tag → grade → split → index.

| Field | Notes |
|---|---|
| `file` | PDF, txt, md. Read page by page for PDFs. Kept byte-for-byte as well as chunked — see [02](02-data-model.md#filesystem--the-original-file-store). |
| `text` | Alternative to `file`. |
| `kind`, `origin` | Admin metadata. |
| `replaces` | An existing source id, to supersede it deliberately. |

**200** → the source card (see `GET /api/sources/{id}`).

**400** — no readable text. A scanned PDF is refused with an explanation rather than
ingested empty.

**409** — the body is already in the library. Detail is an *object*, not a string:
```json
{ "detail": { "message": "This is already in the library as \"…\" (grade 9, ingested 2026-07-27). Nothing was added.",
              "duplicate_of": "<source id>" } }
```
The fingerprint is whitespace-normalised, so re-extracting the same PDF still
matches. Re-upload is refused rather than duplicated because the Reader is
generative: two copies get different titles, summaries and grades and are nearly
invisible in the library. Also raised on a constraint violation from a concurrent
upload, with `duplicate_of: null`.

### `GET /api/sources`
Search, filter, sort, paginate.

| Query | Default | |
|---|---|---|
| `search` | — | Title, summary, origin, author, filename **and full body** |
| `topic`, `kind` | — | Exact match |
| `min_grade`, `max_grade` | 1, 10 | |
| `sort` | `newest` | `newest` `oldest` `grade_desc` `grade_asc` `title` |
| `page`, `per_page` | 1, 10 | |

```json
{ "sources": [ … ], "total": 8, "page": 1, "pages": 2, "per_page": 5 }
```

Search covers the body because the Reader's summary paraphrases: it wrote "iron
absorption" where the source says "ferritin", so a title-and-summary search missed a
source that plainly discusses the term.

### `GET /api/sources/{id}`
The source card: all metadata, `topics[]`, `chunks` count.

### `GET /api/sources/{id}/text`
The source as ingested. `body` plus `passages[]`, each with a `locator`
("page 4", "pages 3–4", "passage 2 of 7"). `body_reconstructed: true` marks a source
ingested before bodies were kept, reassembled from its passages.

### `GET /api/sources/{id}/original`
The uploaded file itself, served with its stored media type and its original filename,
so it keeps a sensible name if saved. Extraction is lossy (tables, figures, layout,
scanned pages); this is the unmediated document behind the passages.

`Content-Disposition` is `inline` only for `application/pdf` and `text/plain` — the
two types worth previewing — and `attachment` for everything else, with
`X-Content-Type-Options: nosniff`. The media type is uploader-supplied and we serve
from the app's own origin, so rendering an uploaded `text/html` inline would be stored
XSS against the gate cookie. The filename is stripped of quotes and control characters
before it goes back into the header.

**404** if the source has no original — pasted text, ingested before the file store
existed, or the archive write failed. Callers should check `original_name` on the
source card rather than probing this endpoint.

### `GET /api/sources/{id}/related`
`{ "concepts": [...], "neighbours": [{ id, title, grade, shared[], n }] }` — what
this source is about and which other sources it connects to.

### `PATCH /api/sources/{id}`
`{ "grade": 1–10 }`. The admin override. **400** outside range, **404** if unknown.

### `DELETE /api/sources/{id}`
Removes the source, its passages, and its stored original file.

### `GET /api/facets`
`{ "topics": [...], "kinds": [...] }` — values actually present, for filter menus.

### `GET /api/graph`
Graph shape plus `unlinked[]` — sources with no concept edges, invisible to
traversal until linked.

### `POST /api/relink`
Indexes concepts for unlinked sources. Returns what was linked and the new stats.

### `POST /api/consolidate`
The LLM tidy pass. Merges labels that are the same idea and rewrites the edges.
```json
{ "concept": { "groups": [{ "canonical": "vitamin d", "aliases": ["cholecalciferol"] }],
               "absorbed": 1, "before": 39 },
  "topic":   { "groups": [], "absorbed": 0, "before": 14 },
  "concepts": 38, "mentions": 79, "order_edges": 8, "source_links": 7 }
```

### `GET /api/coverage`
`[{ topic, sources, chunks }]`, densest first.

### `GET /api/audit`
Both stores merged for display, newest first, each row tagged
`vault: "library" | "patient"`. **Merged only for display** — the storage boundary
is real ([02](02-data-model.md)).

---

## Patients

### `POST /api/patients`
`{ name, country, dob? }` → the patient.

### `GET /api/patients`
`?search=` (name substring) `&country=`. Each row carries `entries` and `sessions`
counts.

### `GET /api/patients/{id}`
The patient plus `entries[]` in chronological order. **404** if unknown.

### `DELETE /api/patients/{id}`
Erases the patient, their entries, sessions and turns; **redacts** their audit
detail while keeping the rows, and logs `patient erased`.

### `POST /api/patients/{id}/entries`
`{ kind, content }`, `kind ∈ lab | history | note | session_summary`. **400** on an
unknown kind.

### `POST /api/patients/{id}/summary`
`{ session_id }` — summarises a stored consultation into the record. Accepts a raw
`transcript` instead. **400** if there is nothing to summarise.

---

## Consultations

### `GET /api/patients/{id}/sessions`
`[{ id, title, started_at, turns }]`, newest first.

### `GET /api/sessions/{id}`
The session and its `turns[]`, each replaying with its citations, verdict and
traversal.

### `POST /api/consult`

```json
{ "patient_id": "…", "question": "…",
  "min_grade": 7, "run_check": true, "session_id": null }
```

`session_id` omitted starts a new consultation; supplied continues one. History is
read from the vault, never trusted from the client, and capped at the last 6 turns.

```json
{
  "session_id": "…",
  "answer": "…[S1]…",
  "matched": true,
  "min_grade": 7,
  "check": { "verdict": "pass", "unsupported": [], "note": "…" },
  "librarian": { "reasoning": "…", "considered": 4,
                 "opened": [{ "title": "…", "grade": 9 }], "truncated": 0 },
  "traversal": { "match": 3, "adjacent": 1, "linked": 0, "opened": 7,
                 "available": 11, "focus": ["ferritin", "iron absorption"] },
  "sources": [{
      "label": "S1", "source_id": "…", "title": "…", "grade": 9,
      "locator": "page 4", "origin": "…", "author": "…", "published": "…",
      "reference": "…", "kind": "protocol", "filename": "…", "snippet": "…",
      "via": "match", "shared": ["ferritin", "iron absorption"]
  }]
}
```

`matched: false` means retrieval found nothing: `answer` is a deterministic refusal,
`check` is `null`, `sources` is empty, and the Specialist was never called.

`via` is `match` | `adjacent` | `linked` | `opened` — how the passage was reached
([04](04-retrieval.md)).

**404** if the patient or the named session does not exist.

---

## Front end

`GET /` — the app shell, or the gate page when unauthenticated.
`POST /gate` — `passphrase` form field. **303** to `/` with the cookie on success,
**401** with the gate page and an error on failure.
`/static/*` — assets, served `Cache-Control: no-store`.

## Conventions

- Errors are `{ "detail": … }`. A **string** for simple errors; an **object** when
  the UI must act on it (only the duplicate-ingest 409 so far). Clients must handle
  both — the front end reads `detail.message` when `detail` is an object.
- Timestamps are ISO 8601 UTC to the second.
- Ids are UUID4 strings; passage ids are `{source_id}:{ordinal}`.
