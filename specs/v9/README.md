# v9 — Backend pipeline latency: brainstorm and recommendation

**Status: spec only — not implemented.**

- [**01 · Candidates, evidence, and the recommended package**](01-latency-brainstorm.md)
- [**02 · Full-stack rearchitecture review (language, frameworks, infra)**](02-rearchitecture-review.md) — decision-grade verdicts on Python vs. Rust, async-ification, durable execution, agent frameworks, Neo4j, and observability.
- [**03 · Living client state (and why the specialist swarm was dropped)**](03-living-client-state.md) — research-backed verdict against a parallel specialist-agent swarm, and a concrete spec for a bi-temporal `client_clinical_state` table replacing recompute-on-every-consult.
