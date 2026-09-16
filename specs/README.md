# Clinic — specifications

Specs are versioned. Each `vN/` folder is a complete, self-contained, frozen
snapshot — enough on its own to audit what was built, or to rebuild the system
from scratch, at that point in time. Nothing in a released version folder is
edited after the fact; a change becomes a new version.

| Version | Status | Covers |
|---|---|---|
| [v6.7](v6.7/README.md) | **implemented, live-verified in production** | SEO/GEO for the public pages (meta/OG/JSON-LD, sitemap.xml, robots.txt naming AI crawlers, llms.txt — plus a same-day bug where the new static files served as the SPA shell instead of their real content); practitioner-owned questionnaires (per-owner active-questionnaire scoping, explicit activate/deactivate, practitioners can view but not edit the site default — with a Pro-only auth gate tightened in review); a portal UX batch (nav notification badges, practitioner/client portals dropping their width cap, a library-source viewer for practitioners, more useful dashboard tiles on all three portals, icons extended beyond admin) |
| [v6.6](v6.6/README.md) | **implemented, live-verified in production** | Two "act as a real user" audits run against the live app: a client-portal audit (wearables page implying real vendor data when it's fixture — fixed with an honest "Coming soon" state; questionnaire ignoring its own typed schema — fixed) and a superadmin-portal audit (an audit trail that was written but never readable — fixed; admin- and client-account management existing on the backend with zero UI — both fixed; a real auth-enforcement gap found while wiring up client suspension — a suspended client could still log in or keep an existing session — fixed). A separate public-page dead-gutter fix (navbar/practitioner-directory) was shipped, then reverted same day at user request |
| [v6.5](v6.5/README.md) | **implemented, live-verified in production** | Lab intake (practitioners and clients can both record labs/conditions/medications/notes, privacy-scoped so a client never sees a practitioner's private entries); model routing spread across three deployments (a dedicated Qwen3-32B endpoint for Reader/Graph-builder/Checker-LLM, Kimi-K3 routed to Nebius's EU-west2 for Reasoner/Answer Engine, a dedicated Qwen3-Embedding-8B endpoint) with two real compatibility bugs fixed (a second thinking-disable mechanism, a much lower max_tokens ceiling); three consult-page bugs found and fixed live, including a real regression — the sidebar going entirely unclickable on first arrival, caused by an uncaught error inside a `$effect` breaking the rest of the component's reactivity |
| [v6.4](v6.4/README.md) | **implemented, live-verified in production** | Consult page rebuilt as a GPT/Claude-style chat interface (persistent sidebar with searchable clients, calendar-badge conversation history, a patient info widget; a bottom-pinned composer; markdown rendering; a closed-by-default sources accordion) — plus a real hallucination fix found while using it: the Reasoner answered a question from topic-adjacent context that didn't actually cover it. Fixed in the Reasoner's system prompt, verified live; also fixed two citation-parsing bugs (an inflated `sources` list, and grouped citation brackets like `[K1, K3]` being silently missed by both the server- and client-side matchers) |
| [v6.3](v6.3/README.md) | **implemented, live-verified in production** | Checker alternatives, triggered by `run_check` defaulting to `false` in production (2026-09-14) because HHEM-2.1-Open still costs 28-77s/call even after the OOM fix. Evaluated four candidates; the recommended first prototype (MiniCheck-RoBERTa-Large) came back **worse** (185.21s/call) — pointed at CPU-only inference on this VPS as the real bottleneck, not model choice. The fourth candidate, a small-LLM-as-judge (`app/reasoning/llm_checker.py`, offloads scoring to Nebius), was prototyped and shipped same-day: 1.2-6.5s/call verified live, `run_check` back to `true` by default. The local HHEM path is untouched and still selectable |
| [v6.2](v6.2/README.md) | **investigated, not implemented** | Retrieval latency follow-up to v6.1, same day: after the TRAVERSAL_MAX_CANDIDATES_PER_HOP fix (20→5) cut a real call from 94.64s to 9.93s, tested five further levers live against production. Four don't hold up (skipping the search-query LLM call trades accuracy for unreliable savings; TRAVERSAL_SEED_TOP_K/MAX_DEPTH have no consistent direction now; the accumulated-context window is noise). Found one real unfixed cost (fetch_hop_neighbors, ~1.3s/hop) and one promising-but-unverified lever (google/gemma-3-27b-it as a faster ANSWER_ENGINE candidate) |
| [v6.1](v6.1/README.md) | **partially implemented** | Ingestion latency audit, prompted by the same-day RETRIEVAL_MODEL/REASONER_MODEL reasoning-token bugs. Ingestion has no reasoning-token problem (Reader/Graph-builder both confirmed non-reasoning). The sequential O(chunks) Graph-builder loop (~26s/10 passages) is now parallelized (~2-3x faster, implemented same day); Embedder's latency turned out highly variable on re-test (1.65-8.59s across runs, not a stable ~9.5s), no app-side fix found. Streaming ingest progress remains undone |
| [v6](v6/README.md) | **implemented, live-verified in production** | Migrated app/core_store.py + app/vault.py from per-file SQLite to a single Postgres database, using a Postgres schema per practitioner to preserve the isolation the separate-file design had on purpose. Run against a real local Postgres instance end-to-end at the time (including migrating this repo's real existing vault data), and against the real production database since (schema-per-practitioner isolation confirmed live, 2026-09-11) |
| [v5](v5/README.md) | **implemented, live-verified in production** | Retirement of app/knowledge.py + app/llm.py: retrieval becomes iterative graph traversal with per-hop LLM-judged relevance pruning (GraphTraversalRetriever), seeded by patient-conditioned vector+full-text search over a new Document/Chunk/Entity Neo4j schema. Patient context now sourced from the existing SQLite vault (no MySQL in this repo); grading and the anti-hallucination Checker carried forward as explicit decisions. Real multi-hop traversals (seed search → graph expansion → grounded answer) confirmed live against production data and a real practitioner account, 2026-09-11 |
| [v4.2](v4.2/README.md) | **implemented, live-verified in production** | Swapped the LLM provider from Anthropic to Nebius's OpenAI-compatible token factory, splitting the 4-role pipeline into 6 (Reader, graph-builder, embedder, retrieval-planner, reasoner, checker); the practitioner-owned-key model was retired for one shared server-side key, and the Checker became a direct anti-hallucination classifier call instead of a chat completion. Real Nebius/Neo4j/HHEM calls confirmed live in production, 2026-09-11 — including finding and fixing two real model-selection bugs (`v4.2/01`'s catalog-id names were never verified against the real Nebius catalog; the first working retrieval model choice ignored strict JSON-schema output entirely) that this spot-check exists specifically to catch |
| [v4.1](v4.1/README.md) | **implemented, partially** | A role-by-role redesign pass on top of deployed v4: splits the landing page from the practitioner directory, a per-role visual/structural separation system for client/practitioner/admin, and a severity-ranked list of gaps and bugs found while auditing all four portals. 01/02 (the split + visual separation) are built; of 03's 28 findings, all 3 Critical and 5/7 High are fixed, 2 High + 11/12 Medium + 5/6 Low remain open (re-audited 2026-09-11 — see [03](v4.1/03-known-issues-and-gaps.md) for per-finding status). 04 (product rename) is still spec-only by design |
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
