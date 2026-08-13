# Clinic — Online Clinic Platform, Phase 1 PoC

> **Specifications:** [`specs/`](specs/) is versioned — see
> [`specs/README.md`](specs/README.md) for the index and
> [`specs/CHANGELOG.md`](specs/CHANGELOG.md) for what changed between
> versions. This README describes the Phase 1 PoC that is actually deployed;
> its spec is [`specs/v1/`](specs/v1/README.md). The current spec version,
> covering the full product (website, admin, practitioner and client
> portals), is [`specs/v2/`](specs/v2/README.md) — not yet built.

A working slice of the solution in `online-clinic-platform-schema_1.pdf`: an admin
curates a graded knowledge library, and a practitioner consults an AI assistant
that answers **only** from that library plus the patient's own record, showing
its sources and verifying itself before the answer is displayed.

PubMed (the third source in the deck) is out of scope for this PoC.

## What it demonstrates

| Claim in the deck | Where you see it |
|---|---|
| The clinic teaches its own AI | Admin → upload a source → the Reader titles, tags, summarises and grades it |
| Every source has a card | Origin, author, publication date, reference, kind, file, pages, passages, size, fingerprint, ingest date, topics, and an adjustable 1–10 grade |
| A source can be corrected or removed | Re-uploading is refused as a duplicate with a one-click "replace it with this upload"; removing asks for confirmation, then drops its passages |
| The original stays readable | "view source" opens the document as ingested, with its metadata and every passage labelled by page |
| Answers show where each claim came from | Every citation carries a locator — "page 4", "pages 3–4", or "passage 2 of 7" — plus author, date and origin, and links to the source |
| The AI shows what it knows | Coverage table (topic → sources, passages) |
| The librarian knows which shelves to check | "How the librarian chose" — its reasoning and the sources it opened |
| A full paper trail | Audit log of every ingest, regrade, deletion and question |
| You control the knowledge | Grade slider — set it to 7 and low-graded sources stop reaching answers |
| Answers are grounded and referenced | Inline `[S1]` citations; click one to jump to the passage |
| An independent check guards each answer | Anti-hallucination badge with the claims it could not verify |
| It remembers | "Save session summary" writes back into the patient record |
| Patient data in its own vault | Knowledge lives in Neo4j, patients in a separate SQLite file |

## The AI team

Every role is an Anthropic model — there is no second AI vendor and nothing runs
locally except the database.

| Role | Model | Job |
|---|---|---|
| Reader | `claude-haiku-4-5` | Reads an incoming source → title, summary, topics, suggested grade |
| Librarian | `claude-sonnet-5` | Reads the catalogue of source cards and picks which sources to open. Does not answer. |
| Specialist | `claude-opus-5` | Writes the grounded, referenced answer from those sources' passages |
| Checker | `claude-haiku-4-5` | Verifies the draft against its passages before it is shown |

**Why the Librarian is Sonnet and not Haiku.** Haiku 4.5 refuses to open a
low-graded source even when the practitioner has explicitly lowered the grade bar
to allow it — it re-litigates reliability on its own ("a low-grade wellness
podcast lacking clinical rigor") despite being told relevance is its only job.
That silently breaks the grade slider in the downward direction, which makes the
control a lie. Sonnet 5 keeps relevance and reliability separate as instructed.
The Librarian is also never shown a source's grade, for the same reason.

### How retrieval works — a connected corpus, traversed

Retrieval is two stages: the Librarian picks which sources to open, then the
library is **traversed** rather than merely read.

Every passage is linked to the concepts it is about (`(:Chunk)-[:MENTIONS]->(:Concept)`)
and to the passage that follows it (`[:NEXT]`). A question is turned into the same
concept vocabulary, and the walk gathers four kinds of passage — each labelled in
the answer so the context is auditable:

| Hop | What it finds | Why it matters |
|---|---|---|
| `match` | A passage mentioning a question concept, **wherever it sits** | Reaches page 11 of a long protocol instead of losing it to the passage budget |
| `adjacent` | The reading-order neighbours of a match | Rejoins a claim split across a passage boundary |
| `linked` | A passage in **another** source sharing ≥ `MIN_SHARED_CONCEPTS` | Answers from material the Librarian never opened |
| `opened` | The remaining budget, in reading order | A short source still arrives whole |

Verified: with the budget squeezed to 4 passages against a 9-passage protocol, the
iron-dosing appendix in **passage 9 of 9** still reached the answer, matched on
`iron deficiency, ferritin, iron absorption`, with passage 8 alongside it for
context. Reading-order truncation would have taken passages 1–4 and missed it.

**Concepts converge on one label per idea**, or there is no edge. Two mechanisms:
a deterministic alias table (`Fe`, `ferrous`, `serum iron` → `iron`; `25(OH)D`,
`cholecalciferol` → `vitamin d`; `HT`, `Hashimoto's` → `hashimoto thyroiditis`)
applied at both index and query time, plus an LLM consolidation pass ("Tidy the
index") that merges the tail a static map cannot anticipate. That pass is
deliberately conservative — it merged `cholecalciferol → vitamin d` and refused to
merge `ferritin` with `iron`, which are different measures.

Topics work the same way: the Reader is shown the shelves the library already uses
and reuses one where it fits, coining a new topic only when nothing covers the
source.

### Source selection — card-based, not vector search

Anthropic has no embeddings API, so this PoC does not do semantic vector search.
Instead the Librarian is shown the **catalogue of source cards** (title, origin,
topics, one-line summary, grade) for every source at or above the practitioner's
grade bar, and picks which ones to open. The chosen sources' passages become
`[S1]`, `[S2]` … for the Specialist.

This lands closer to the deck's own metaphor — *"you ask a question, she knows
exactly which shelves to check"* — and it makes the grade filter absolute: a
source below the bar is never offered to the Librarian at all, so it cannot reach
an answer by any path.

**The tradeoff, stated plainly:** the whole catalogue rides in the Librarian's
prompt, so this works to roughly a few dozen sources and then stops scaling.
Retrieval also happens at source granularity, not passage granularity — opening a
long source sends all of it. `MAX_SOURCES` and `MAX_PASSAGES` bound that, and the
API reports when either one truncated the material rather than dropping it
silently. A production library needs real embeddings (Voyage, or a local model).

## Deployed

Live at `http://43.156.136.92`, access phrase `DevshorePartners2026`. Intended for
`telehealth.devshorepartners.id` — **the Cloudflare DNS record still needs to be
pointed at the server**. See [DEPLOY.md](DEPLOY.md).

## Running it locally

Prerequisites: Neo4j running locally and an Anthropic API key.

```bash
cp .env.example .env          # then put a real ANTHROPIC_API_KEY in .env
brew services start neo4j

.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

Open http://localhost:8000. The header shows a live status dot for Neo4j and
Anthropic — both must be green.

To check the whole pipeline in one command against a running server:

```bash
.venv/bin/python verify.py
```

It ingests a strong and a weak source, creates a patient with labs, asks the same
question at grade ≥7 and grade ≥1, asserts the weak source is excluded then
included, checks an unanswerable question is refused rather than invented, saves a
session summary, and deletes a source to confirm it leaves the library.

## Demo script

1. **Admin portal** → paste a clinical protocol, set origin, Ingest. Watch the
   Reader's source card appear with its topics and suggested grade.
2. Ingest a deliberately weak source (a podcast transcript on the same topic).
   Note the Reader grades it low on its own.
3. **Practitioner portal** → create a patient, add a lab (`Ferritin 11 ng/mL`)
   and a line of history.
4. Ask *"Her vitamin D is low and her ferritin is low — what could that be tied
   to?"* The answer cites `[S1]`; the sources panel shows which passages and at
   what grade; "How the librarian chose" shows it considered 1 card of 2.
5. Now ask something the weak source overreaches on — *"Can vitamin D alone
   reverse Hashimoto's, and is 50,000 IU daily appropriate?"* At grade ≥7 the
   podcast is unreachable. **Drag the slider to 1 and ask again**: the librarian
   now opens it, and the Specialist cites it *while contradicting it* against the
   protocol. That is the whole product in one interaction — the clinic decides
   what the AI may see, and the AI stays honest about what each source supports.
6. Save the session summary; it lands in the patient record and is in context
   for the next question.

The grade bar governs what the librarian is *offered*. Which of those it opens is
its own relevance judgement, so a question no source addresses yields no sources
at any grade — visible in the same panel.

## Layout

```
app/config.py      env-driven settings
app/knowledge.py   Neo4j: sources, passages, topics, catalogue, audit
app/patients.py    SQLite: patients and record entries
app/llm.py         the AI team, one function per role
app/main.py        FastAPI routes
static/            single-page frontend, no build step
```

## Deliberate PoC limits

- No auth, no multi-user. Country is a field on the patient, not a storage boundary.
- Patient files are passed whole to the Specialist rather than retrieved over —
  correct at this scale, would need retrieval for large records.
- Card-based retrieval does not scale past a few dozen sources, and opens whole
  sources rather than individual passages (see above).
- **Only exact duplicates are caught.** Each source is fingerprinted by a hash of
  its body (whitespace-normalised, so re-extracting the same PDF matches), and a
  re-upload is refused with a 409 naming the existing source plus a one-click
  replace. This matters because the Reader is generative: two copies of one
  document get different titles, summaries and grades, so a duplicate is nearly
  invisible in the library view. What is *not* built is the deck's fuller promise
  of "duplicates and contradictions flagged for review" — a lightly edited second
  edition, or two sources that contradict each other, both pass unnoticed. That
  needs semantic comparison, not a hash.
- Scanned (image-only) PDFs are rejected with a clear message rather than
  silently ingested empty; OCR is not included.
