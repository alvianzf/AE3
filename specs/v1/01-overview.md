# 01 · Overview

## Purpose

Clinic is a digital clinic for hormonal health whose differentiator is a
**source-grounded** AI assistant. A practitioner asks a question during a
consultation and receives an answer built only from:

1. the clinic's own curated, graded knowledge library, and
2. that patient's own record.

Never from the model's general training. Every clinical claim carries a reference
to the passage it came from, and an independent model verifies the draft before
the practitioner sees it.

The product argument is **control**: the clinic decides what its AI may know, and
can prove what any given answer rested on.

## Actors

| Actor | Uses | Responsible for |
|---|---|---|
| **Knowledge admin** | Admin portal | Adding sources, setting reliability grades, watching coverage |
| **Practitioner** | Practitioner portal | Patient records, consultations, deciding what to do with an answer |
| **Patient** | — | Not a user in this phase. Clinic never speaks to a patient. |

## The five AI roles

Named because the deck names them, and because each is a separate, auditable step.

| Role | Job |
|---|---|
| Reader | Reads an incoming source: titles, summarises, tags topics, proposes a grade |
| Indexer | Extracts the concepts of each passage, so passages can find each other |
| Librarian | Picks which sources to open for a question. Never answers. |
| Specialist | Writes the grounded, referenced answer |
| Checker | Verifies each claim against its cited passages before display |

Detail in [03 · The AI team](03-ai-team.md).

## In scope

- Admin portal: ingest (file or paste), source cards with full provenance,
  reliability grading, duplicate detection, full-text reading, coverage dashboard,
  graph statistics, audit trail
- Practitioner portal: patient CRUD and erasure, record entries, multi-turn
  consultations persisted per patient, grade threshold control, verification
  toggle, session summary written back into the record
- Graph retrieval over the corpus: concept links, reading-order links, and a
  four-hop traversal ([04](04-retrieval.md))
- A single shared access passphrase in front of the whole application
- Two physically separate stores, so patient data never enters the library

## Out of scope — deliberately

| Not built | Why |
|---|---|
| **PubMed / live world research** | Excluded from this phase by request. The deck's third source. |
| **Vector / semantic search** | Anthropic has no embeddings API and the stack is Anthropic-only. Relatedness comes from concept links instead ([04](04-retrieval.md)). |
| **User accounts, roles, real authentication** | A PoC. The passphrase is a door code, not auth ([07](07-security.md)). |
| **Country data residency** | Country is a field on the patient, not a storage boundary. |
| **Telehealth video, patient-facing app** | Later phases in the deck. |
| **Backups, rate limiting, observability** | Not production. |

## Constraints that shaped the design

1. **Anthropic-only.** No second AI vendor and nothing local except the database.
   This is why retrieval is concept-graph based rather than vector based.
2. **1.9 GB host.** Neo4j runs with a 512 MB heap; there is no headroom for a
   second JVM. See [08](08-operations.md).
3. **Grounding must be structural, not hoped for.** Where a guarantee can be made
   by *not calling the model*, it is: with no passages retrieved, the Specialist is
   never invoked ([04](04-retrieval.md#no-match)).

## Success criteria

The PoC is done when all of these hold, and `verify.py` asserts each one:

1. A source can be ingested and is read, tagged, graded and split automatically.
2. An answer cites its sources, each with a locator naming where in the document
   the claim came from.
3. Raising the grade threshold demonstrably removes weak sources from answers;
   lowering it lets them back in.
4. A question the library cannot answer is refused, not invented.
5. A consultation is a conversation — follow-ups resolve against earlier turns.
6. A session summary is written into the patient record and is in context next time.
7. Patient data never appears in the knowledge library, audit trail included.
8. Material deep inside a long document is reachable, not lost to the passage
   budget.

See [09 · Verification](09-verification.md) for how each is tested.
