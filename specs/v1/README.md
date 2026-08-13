# Clinic — specifications (v1 · Phase 1 PoC)

> **Superseded.** This version describes the Phase 1 proof of concept only —
> single shared-passphrase access, one practitioner portal, no billing, no
> public website. It is kept exactly as it was when frozen, for provenance and
> rebuild. For the current spec, see [`../v2/`](../v2/README.md) and
> [`../CHANGELOG.md`](../CHANGELOG.md).

Specification for **Clinic**, the Phase 1 proof of concept of the online clinic
platform described in `online-clinic-platform-schema_1.pdf`.

These documents describe the system **as built and deployed**, not an aspiration.
Where the implementation departs from the original deck, the departure and its
reason are stated. Where a limit exists, it is written down rather than left for
someone to discover.

| # | Document | Covers |
|---|---|---|
| 01 | [Overview](01-overview.md) | Purpose, actors, scope, and what is deliberately out of scope |
| 02 | [Data model](02-data-model.md) | The two stores, their schemas, and why they are separate |
| 03 | [The AI team](03-ai-team.md) | Five roles, model choices, and the contract of each call |
| 04 | [Retrieval](04-retrieval.md) | Source selection and the graph traversal algorithm |
| 05 | [HTTP API](05-api.md) | Every endpoint, its shape, and its failure modes |
| 06 | [Front end](06-frontend.md) | Information architecture, flows, and the design system |
| 07 | [Security & privacy](07-security.md) | The access gate, vault separation, and what is not protected |
| 08 | [Operations](08-operations.md) | Deployment topology, configuration, and runbook |
| 09 | [Verification](09-verification.md) | The test suite and what each check actually proves |

## Reading order

Read **01** then **04**. Retrieval is where the product argument lives: everything
else exists to make grounded, cited, grade-controlled answers possible.

## Status

| | |
|---|---|
| Live at | https://telehealth.devshorepartners.id |
| Access | single shared passphrase (see 07) |
| Stack | FastAPI · Neo4j · SQLite · Anthropic · vanilla JS |
| Verified by | `verify.py` — 12 checks, run against the live deployment |

## Related documents

- [`../../README.md`](../../README.md) — orientation and the demo script
- [`../../DEPLOY.md`](../../DEPLOY.md) — the deployment runbook
- [`../../PLAN.md`](../../PLAN.md) — the approved build plan, with its amendments
- [`../../archive/`](../../archive/) — superseded specs from the earlier DUTCH
  GraphRAG effort, kept only for provenance
