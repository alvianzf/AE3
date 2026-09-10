# Clinic — specifications

Specs are versioned. Each `vN/` folder is a complete, self-contained, frozen
snapshot — enough on its own to audit what was built, or to rebuild the system
from scratch, at that point in time. Nothing in a released version folder is
edited after the fact; a change becomes a new version.

| Version | Status | Covers |
|---|---|---|
| [v6](v6/README.md) | **implemented, live-verified locally** | Migrated app/core_store.py + app/vault.py from per-file SQLite to a single Postgres database, using a Postgres schema per practitioner to preserve the isolation the separate-file design had on purpose. Unlike this session's other changes, this was actually run against a real local Postgres instance end-to-end, including migrating this repo's real existing vault data |
| [v5](v5/README.md) | **implemented, not live-verified** | Retirement of app/knowledge.py + app/llm.py: retrieval becomes iterative graph traversal with per-hop LLM-judged relevance pruning (GraphTraversalRetriever), seeded by patient-conditioned vector+full-text search over a new Document/Chunk/Entity Neo4j schema. Patient context now sourced from the existing SQLite vault (no MySQL in this repo); grading and the anti-hallucination Checker carried forward as explicit decisions |
| [v4.2](v4.2/README.md) | **implemented, not live-verified** | Swapped the LLM provider from Anthropic to Nebius's OpenAI-compatible token factory, splitting the 4-role pipeline into 6 (Reader, graph-builder, embedder, retrieval-planner, reasoner, checker); the practitioner-owned-key model was retired for one shared server-side key, and the Checker became a direct anti-hallucination classifier call instead of a chat completion. Code-confirmed only — needs a real Nebius/Neo4j/HHEM spot-check before trusting in production |
| [v4.1](v4.1/README.md) | **spec only, not built** | A role-by-role redesign pass on top of deployed v4: splits the landing page from the practitioner directory, a per-role visual/structural separation system for client/practitioner/admin, and a severity-ranked list of gaps and bugs found while auditing all four portals (3 Critical functional bugs, plus High/Medium/Low workflow gaps) |
| [v4](v4/README.md) | **deployed — actually current** | A SvelteKit frontend rewrite, plus post-launch work: a PM/QA/Clinician review (42/44 fixed), CI/CD, chunked uploads, a staged-source review queue |
| [v3](v3/README.md) | superseded in practice, not yet formally cut | v2 plus bounded AI-answer revision, a reachable Summariser, and Material Design 3 |
| [v2](v2/README.md) | superseded | Full product: public website, admin portal, practitioner portal, client portal |
| [v1](v1/README.md) | superseded | Phase 1 PoC: single-passphrase access, one practitioner portal, RAG over a graded library |

**This table is honest about a real gap, not just stale**: `v4` has been
deployed to production since commit `5e0c14f` (2026-09-02), but the formal
cut this doc's own convention below describes — copying forward every
unchanged `v3/` doc, freezing `v3/` — has never been done. Until it is,
[`v4/README.md`](v4/README.md) is the accurate index of what's real;
`v3/`'s docs are still individually correct wherever `v4/` doesn't
explicitly supersede them, per `v4/README.md`'s own "Everything else"
section.

See [`CHANGELOG.md`](CHANGELOG.md) for what changed between versions and why.

## Working convention

- Never edit a spec inside a released `vN/` folder. If reality has moved on
  from what's written, that's a signal to cut the next version, not to patch
  the old one.
- A new version is cut when there's a change worth auditing: new scope, a
  reversed decision, a data-model change — not for typo fixes within an
  in-progress version.
- Bump the folder (`v3/`, ...), copy forward the docs that didn't change,
  rewrite the ones that did, and add an entry to `CHANGELOG.md` explaining the
  why.
- This `README.md` always points at the current version.
