# 09 · Verification

`verify.py` drives the real HTTP API end to end and asserts the behaviours the PoC
exists to prove. It runs against a local server or the live deployment:

```bash
.venv/bin/python verify.py
CLINIC_URL=https://telehealth.devshorepartners.id .venv/bin/python verify.py
```

It passes the access gate like a browser (cookie jar plus a named `User-Agent`, or
Cloudflare answers 1010) and prints what it found, not just pass/fail — the printed
output is the evidence.

## It does not touch your data

Two properties, both deliberate, both added after the script polluted a live library:

1. **Run-unique fixtures.** Every fixture carries `verify-run-<id>`, so its
   fingerprint can never collide with a source you ingested — the duplicate check
   will never offer to replace *your* content.
2. **It cleans up and proves it.** Its sources and its test patient are deleted at
   the end, and the final assertion is that the library count returned to what it
   was on entry.

## The checks

| # | Check | What it actually proves |
|---|---|---|
| 0 | Access gate | An `/api` route returns 401 without the cookie; the phrase then opens it. Gating the HTML alone would not be enough. |
| 1 | Health | Neo4j, Anthropic and the vault are all reachable. Catches a placeholder API key immediately. |
| 2 | Ingestion | A source is read, titled, summarised, tagged, graded 1–10 and split into passages, unattended. |
| 2b | Duplicate refusal | A re-upload is refused with a 409 pointing at the original, and **no copy is created**. Whitespace-only differences are still caught. An explicit `replaces` supersedes deliberately without changing the source count. |
| 2c | Metadata & provenance | The card carries author, published, reference, kind, origin, filename, page and character counts, and a fingerprint. The original body is readable and every passage has a locator. |
| 3 | Patient record | A patient and their entries are created in the vault. |
| 4 | **Grade filter** | At grade ≥7 no sub-threshold source is cited, the answer carries `[S1]`, and each citation has a locator plus provenance. |
| 5 | Threshold widens the catalogue | Lowering the bar increases what the Librarian is offered, and nothing below the bar is ever cited. Asserted as an **invariant**, not an exact count, so the check survives whatever else is in the library. |
| 5b | Reachability both ways | A question the weak source overreaches on: at grade ≥7 the podcast is unreachable; at ≥1 the Librarian opens it — and the Specialist cites it *while contradicting it* against the protocol. |
| 6 | Grounding | A question the library cannot answer opens nothing and is refused. The Specialist is never called. |
| 7 | Summary write-back | A consultation is summarised into the record and is in context next time. |
| 7b | **Vault separation** | No library-store audit row contains the patient's name, id, or the question text, and no patient-touching action appears there. |
| 8 | Coverage, audit, deletion | Deleting a source drops its passages and it stops being cited. |
| 9 | Untagged-source regression | A source with no topics still gets its passages written. Skipped against a remote target — it calls the store directly and would otherwise test the wrong database. |

## Why some checks are shaped oddly

**Step 2 forces the grades.** The Reader's grade is a genuine judgement and is not
deterministic — the same podcast has scored 2 and 4 on different reads. If both
fixtures happened to land near each other, the grade-filter test would prove nothing.
So the script pins 9 and 3 before testing the filter. In a live demo the Reader's own
suggestion is the interesting part; here determinism matters more.

**Step 5 asserts an invariant, not a number.** An earlier version hardcoded "2 cards
at grade 1" and broke the moment the library held anything else. Tests that only pass
on an empty database are not worth much.

**Step 7b was proved by breaking it.** The leak was reintroduced deliberately; the
check failed, then passed once reverted. A regression test that has never failed has
not been shown to work.

## Verified outside the script

Recorded here because the assertions live elsewhere, or the evidence is a rendered
screenshot.

| Property | How |
|---|---|
| **Chunking loses nothing** | Every word of the input appears in some passage — tested on many short paragraphs, a single 1500-word paragraph, five dense pages, and a real 8-page PDF. |
| **Traversal reaches deep material** | `MAX_PASSAGES=4` against a 9-passage protocol: the iron-dosing appendix in **passage 9 of 9** still reached the answer, matched on `iron deficiency, ferritin, iron absorption`, with passage 8 alongside. Reading-order truncation would have missed it. |
| **Concept canonicalisation** | 24 cases including `Fe`/`ferrous`/`serum iron` → `iron`, `25(OH)D`/`cholecalciferol` → `vitamin d`, `HT`/`Hashimoto's` → `hashimoto thyroiditis`, and clinical nouns that must keep a trailing *s* (`thyroiditis`, `diabetes`, `analysis`). |
| **Consolidation is conservative** | Merged `cholecalciferol → vitamin d`; refused to merge `ferritin` with `iron`. |
| **Librarian model choice** | Same question and catalogue across Haiku 4.5, Sonnet 5, Opus 5: Haiku vetoed an allowed low-graded source, the other two did not. |
| **Cold boot** | Reboot twice; healthy ~95 s, `NRestarts=0`, data intact. |
| **Deployed code matches local** | SHA-256 per file, plus the Cloudflare-served asset hashes. |
| **UI correctness** | Headless-Chrome screenshots of every state. This is what caught the invisible full-page overlay, the stale-cache empty library, the citation-chip spacing, and the run-together name and metadata ([06](06-frontend.md)). |

## Gaps

- No unit tests. Everything is end-to-end, which is slower and costs real API calls.
- No automated front-end tests; UI verification is screenshots read by eye.
- No load or concurrency testing. The duplicate-ingest race is handled by a database
  constraint but has not been driven concurrently.
- The Checker's negative path is not asserted — it fires on weak grounding, which is
  hard to force reliably. Only its positive verdict is checked.
