# 04 · Retrieval

The core of the product. Two stages: choose which sources to open, then **traverse**
the corpus rather than merely read them.

```
question + patient file + history
   │
   ├─▶ catalogue(min_grade)          sources at or above the grade bar
   ├─▶ Librarian                     which of them to open, and why
   ├─▶ question_concepts()           the question in the index's vocabulary
   ├─▶ traverse()                    four hops over the graph
   ├─▶ Specialist                    the grounded answer  (skipped if nothing found)
   └─▶ Checker                       verify before display
```

## Stage 1 · source selection

Card-based, not vector search: Anthropic has no embeddings API and the stack is
Anthropic-only. The Librarian is shown the catalogue of source cards — title, kind,
origin, author, published, topics, summary — for every source at or above the
practitioner's grade threshold, and picks which to open.

This lands closer to the deck's own metaphor (*"she knows exactly which shelves to
check"*) and it makes the grade filter **absolute**: a source below the bar is never
offered, so it cannot reach an answer by any path, including traversal.

**Limit:** the whole catalogue rides in the prompt, so this works to roughly a few
dozen sources. Beyond that it needs real embeddings.

## Stage 2 · traversal

### The problem this solves

The naive approach — take every passage of the opened sources in reading order and
truncate at the passage budget — **loses anything deep in a long document**. A
relevant paragraph on page 11 of a 40-page protocol simply never arrives.

So passages are gathered by relevance and connection, not by position.

### The four hops

Each passage is labelled with how it was reached, and that label is surfaced in the
UI, so the context behind an answer is auditable.

| Hop | Cypher shape | Finds |
|---|---|---|
| **`match`** | `(src)-[:HAS_CHUNK]->(c)-[:MENTIONS]->(k:Concept)` where `k.name ∈ focus` | A passage on point, **wherever it sits** in the document. This is what reaches page 11. |
| **`adjacent`** | `(match)-[:NEXT]-(c)` | The reading-order neighbours of a match, so a claim split across a boundary is rejoined and the match keeps its context. |
| **`linked`** | `(match)-[:MENTIONS]->(k)<-[:MENTIONS]-(c)` in a **different** source | Passages sharing ≥ `MIN_SHARED_CONCEPTS` with a match. Answers from material the Librarian never opened. |
| **`opened`** | the rest of the opened sources, in reading order | Fills the remaining budget, so a short source still arrives whole. |

Selection is first-hop-wins: a passage already taken is not re-taken by a later hop.
Priority for the budget is `match` → `adjacent` → `linked` → `opened`, with `linked`
ranked by shared-concept count. What survives the budget is then **re-sorted into
reading order**, which is easier for the model to follow than relevance order.

`min_grade` is enforced at *every* hop. Traversal can never smuggle in a source the
practitioner excluded.

### Focus concepts

The question is converted into the same vocabulary the Indexer used, by the same
prompt with a different framing — including concepts implied by the patient's labs
and by earlier turns, not only the words in the question. The result is passed
through `canon()`, or `Fe` in a question would never meet the `iron` node the
indexer wrote.

### Verified behaviour

With `MAX_PASSAGES=4` against a 9-passage protocol whose only iron-dosing text sat
in an appendix:

```
focus:  iron deficiency, iron absorption, ferritin, hashimoto thyroiditis, malabsorption …
hops:   match 3 · adjacent 1 · linked 0 · opened 7 · available 11

S1 [adjacent] passage 8 of 9   Comprehensive thyroid management protocol
S2 [match   ] passage 9 of 9   Comprehensive thyroid management protocol
                               shares: iron deficiency, ferritin, iron absorption
S3 [match   ] passage 1 of 1   Iron deficiency without anaemia
S4 [match   ] passage 1 of 1   Vitamin D Deficiency and Thyroid Function
```

**Passage 9 of 9 reached the answer under a 4-passage budget.** Reading-order
truncation would have taken passages 1–4 and missed it. The Specialist then tied
the sources together: *"Both sources converge on this… the library gives two dose
statements [S2][S3]."*

## No match {#no-match}

When traversal returns nothing, the Specialist is **not called**. A deterministic
message is returned instead, carrying the Librarian's reasoning and the number of
sources that were available at that grade, and the response sets `matched: false`.

This is a structural guarantee rather than a prompted one. It is also ~5 seconds
instead of ~40, and costs no Opus call.

## Configuration

| Key | Default | Effect |
|---|---|---|
| `MIN_GRADE` | 7 | Default grade threshold; the practitioner overrides per question |
| `MAX_SOURCES` | 100 | Cap on sources the Librarian may open. Effectively no limit at PoC scale — its relevance judgement is the real filter. |
| `MAX_PASSAGES` | 120 | The binding constraint. Bounds the Specialist's prompt. |
| `MIN_SHARED_CONCEPTS` | 2 | Concepts two passages must share to be linked. 1 is too loose — `vitamin d` alone links almost everything. |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 1200 / 150 | Passage size in characters |

Truncation is never silent: the response reports `librarian.truncated` and the full
`traversal` breakdown, and the UI prints both.

## Chunking

Paragraph-aware, page-tracking, with overlap. Verified for **coverage**: every word
of the input survives into at least one passage, tested on many short paragraphs, a
single 1500-word paragraph, five dense pages, and a real 8-page PDF.

A passage that straddles a page break records both ends, so a locator can read
"pages 3–4".

## Known limits

1. **Concept co-mention is not semantic similarity.** Two passages sharing
   `ferritin` and `fatigue` are linked even if one is a rigorous review and the
   other a blog. The grade filter is what protects the clinician, and it is enforced
   at every hop. This is the honest ceiling of an Anthropic-only stack.
2. **Source-granularity selection.** The Librarian opens whole sources; only the
   traversal is passage-level.
3. **Catalogue in the prompt** caps the library at a few dozen sources.
4. **Concepts must match exactly** to create an edge. The alias table plus the
   consolidation pass mitigate this; they do not eliminate it.
