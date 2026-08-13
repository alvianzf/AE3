# 03 · The AI team

Five roles, each a separate call with its own model, prompt and output contract.
Separation is not decoration: it is what makes the pipeline auditable, and it is
what lets one role be constrained without weakening another.

All roles are Anthropic models. There is no second AI vendor and nothing runs
locally except the database.

| Role | Model (default) | Output | Called |
|---|---|---|---|
| Reader | `claude-haiku-4-5` | structured | once per ingest |
| Indexer | `claude-haiku-4-5` | structured | once per ingest, once per relink |
| Librarian | `claude-sonnet-5` | structured | once per question |
| Specialist | `claude-opus-5` | prose | once per question, **only if passages exist** |
| Checker | `claude-haiku-4-5` | structured | once per question, when verification is on |
| Consolidator | `claude-sonnet-5` | structured | on demand (Tidy the index) |
| Summariser | `claude-haiku-4-5` | prose | on demand (Save to record) |

Overridable via `READER_MODEL`, `LIBRARIAN_MODEL`, `ANSWER_MODEL`, `CHECKER_MODEL`.

## API usage notes

- Structured roles use `output_config.format` with a JSON schema, so the shape is
  enforced at the API layer and the model retries on mismatch rather than the code
  parsing hopefully.
- Specialist: `thinking={"type": "adaptive"}` (Opus 5's default), `effort: medium`,
  `max_tokens: 8000`. **Do not** pass `thinking={"type":"disabled"}` — on Opus 5 that
  can leak `<thinking>` tags into the visible answer and emit tool calls as plain
  text.
- Haiku 4.5 does not accept `output_config.effort`; passing it errors.
- `temperature` / `top_p` are not accepted on Opus 5.

---

## Reader

Reads an incoming source and produces its card.

**Returns** `title`, `summary`, `topics[]` (1–4), `suggested_grade` (1–10),
`author`, `published`, `reference`.

Two instructions carry the weight:

1. **Be honest about weak sources.** Peer-reviewed guidelines and protocols belong
   at the top; a podcast asserting mechanisms without evidence belongs near the
   bottom. The clinic relies on this number to decide what practitioners see.
2. **Report provenance only if the text states it.** Empty string rather than an
   inferred author or a reconstructed citation.

**Topics converge.** The Reader is given the topics already in the library and told
to reuse one where it genuinely fits, coining a new one only when nothing covers the
source. Without this it invents a near-synonym per document (`thyroid`,
`hashimoto's`, `autoimmune thyroid disease` for one source) and the coverage
dashboard becomes unreadable.

The grade is a **suggestion**. It is not deterministic — the same podcast has been
graded 2 on one read and 4 on another — which is precisely why the admin has an
override slider.

## Indexer

Extracts 3–8 concepts per passage in **one call for the whole document**, so the
model sees the passages together and labels them consistently.

The prompt insists on normalisation, because the mechanism only works if two
passages in different documents emit an identical string: lowercase, singular, no
units, the common clinical name over an abbreviation, and the *mechanism* named
where a passage explains one (`iron absorption`, `hepcidin`) rather than only the
topic. Output is then passed through `canon()` regardless — asking is not a
guarantee ([02](02-data-model.md#concept-canonicalisation)).

Failure is non-fatal: if extraction fails, the source is still ingested, just
unlinked, and `POST /api/relink` can connect it later. Losing a source because its
index failed would be the wrong trade.

## Librarian

Given the question, the patient file, the conversation so far, and the catalogue of
source cards at or above the grade threshold, returns the source numbers worth
opening plus one sentence of reasoning.

Three constraints:

1. **It does not answer.** It gathers.
2. **It judges relevance only.** Reliability was already decided by the grade
   threshold. It is told so explicitly, and it is **never shown a source's grade**.
3. **Follow-ups resolve against history.** "And the dose?" is about the previous
   turn's subject.

### Why Sonnet and not Haiku

Haiku 4.5 refuses to open a low-graded source even when the practitioner has
lowered the bar to allow it — it re-litigates reliability on its own ("a low-grade
wellness podcast lacking clinical rigor") despite being told relevance is its only
job. That **silently breaks the grade slider downward**, which makes the control a
lie. Tested across tiers: Haiku vetoed, Sonnet 5 and Opus 5 both separated relevance
from reliability as instructed. Withholding the grade was added for the same reason.

## Specialist

Writes the answer from the retrieved passages and the patient file.

Rules given: cite the passage behind each clinical point as `[S1]`; say plainly when
the passages do not cover the question and never fill the gap from general
knowledge; connect the passages to *this* patient's labs; be direct.

It is also told that some passages arrived by traversal — one may continue from
another or cover the same subject in a different document — and to use them on the
same footing, saying so where two sources bear on each other.

**It is not called at all when retrieval returns nothing.** A deterministic refusal
is returned instead. Relying on the prompt to make it decline leaves a real chance
of it answering from training; not calling it makes that impossible.

## Checker

Independently verifies the draft against the passages it cites. Returns
`verdict` (`pass` | `weak`), `unsupported[]`, and a one-sentence note.

The first version was **wrong in a way worth recording**: told to "default to weak
when uncertain", it flagged a correct answer, claiming a passage did not state
something it stated verbatim. A checker that always says "needs review" is worthless.

It now must find a *specific* unsupported claim before returning weak, is told that
restating a passage in different words **is** support, and that an empty
`unsupported` list with a `weak` verdict is contradictory.

## Consolidator

Given every label in use, groups the ones that are the same idea and names a
canonical form. Instructed to merge only identical ideas and explicitly warned off
related or hierarchical pairs — `ferritin`/`iron`, `hypothyroidism`/`hashimoto
thyroiditis`, `oestrogen`/`progesterone` — because merging those would make the
library claim two passages are about the same thing when they are not. Returning an
empty list is stated to be the correct answer for a clean index.

## Cost and latency shape

| Operation | Calls |
|---|---|
| Ingest a source | Reader + Indexer (2 Haiku) |
| A question, answered | Focus concepts (Haiku) + Librarian (Sonnet) + Specialist (Opus) + Checker (Haiku) |
| A question with no match | Focus concepts + Librarian only — ~5 s instead of ~40 s, and no Opus call |
| Save a summary | 1 Haiku |
| Tidy the index | 1 Sonnet per label type |

The no-match path being cheap is a consequence of the grounding guarantee, not a
separate optimisation.
