# v3 — Bounded AI revision, reachable Summariser, Material Design 3

Cut from a three-agent (PM/Analyst/Architect) review of the AI pipeline,
requested after the question "can we make the agents talk to each other?"
The review's conclusion was **no, not as a general capability** — see
[07 · The AI team](07-ai-team.md) for why — but it did surface one real gap
(the Checker's verdict went nowhere), one orphaned feature (the Summariser
was fully built and never wired to a route), and a handful of security
findings, all closed in this version. Separately, the front end moves from
hand-written CSS/JS to Material Design 3 via Material Web components — the
project's first build step.

## What's new vs. v2

- **Bounded Checker → Specialist retry** ([07](07-ai-team.md)): a `weak`
  verdict now triggers exactly one revision attempt, capped in code, not a
  general agent-to-agent loop.
- **Summariser reachable**: new `POST
  /api/me/clients/{id}/sessions/{session_id}/summary` route
  ([08](08-api.md)) wires up a role that existed since v1 but was never
  called from anywhere.
- **HTTP `QUERY` method**, experimental, on three filter-heavy read
  endpoints, with `POST` kept as fallback ([08](08-api.md)).
- **Two hardcoded fallback secrets fixed** — `session_secret` and
  `neo4j_password` now fail closed in production instead of silently
  defaulting ([10](10-security.md)).
- **Material Design 3** via `@material/web`, with a real build step
  (`npm` + Vite) for the first time in this project's history
  ([15](15-design-system.md), [11](11-operations.md#build-step)).
- **Live agent-progress toast** during a consultation: which of the seven
  roles is currently running, plus a live running token count, via a new
  SSE stream on `POST /api/me/consult` ([08](08-api.md#live-progress-stream),
  [15](15-design-system.md#live-agent-toast)).
- **Error handling added** to the consultation path — an Anthropic API
  failure now returns a structured 502 instead of an unhandled exception
  ([08](08-api.md#failure-modes)).

## What's explicitly not in this version

- **General agent-to-agent messaging** — considered, rejected. See
  [07](07-ai-team.md#what-did-not-change-and-why).
- **A workflow/orchestration framework** (LangGraph, CrewAI, etc.) —
  considered, rejected as disproportionate for a seven-function pipeline.
- **Librarian empty-result fallback UX** (grade-threshold broadening
  suggestion, admin "add a source" nudge) — a real "should" finding from the
  review, deferred to a follow-up version rather than bundled with a
  frontend rewrite and a build-tooling change in the same release.
- Everything v2 already deferred (email/notifications infrastructure,
  practitioner hard-deletion, encryption at rest for SQLite, backups,
  GDPR apparatus) — unchanged, see [v2/10-security.md](../v2/10-security.md).

## Docs carried forward unchanged

[01](01-overview.md), [02](02-data-model.md), [03](03-website.md),
[04](04-admin-portal.md), [05](05-practitioner-portal.md),
[06](06-client-portal.md), [09](09-payments.md), [12](12-verification.md),
[13](13-known-issues.md), [14](14-ux-findings-v2.7.md), [CONTRACTS](CONTRACTS.md) —
copied byte-for-byte from v2; nothing in their content changed this version.

## Docs rewritten this version

[07](07-ai-team.md), [08](08-api.md), [10](10-security.md),
[11](11-operations.md).

## New this version

[15 · Design system](15-design-system.md),
[16 · `/admin/users` redesign](16-users-page-redesign.md),
[17 · Full-app redesign](17-full-app-redesign.md),
[18 · Document ingest upgrade](18-document-ingest-upgrade.md) (spec only,
not yet implemented — staged uploads, a PDF viewer, and a web-page
scraper), [TODO.md](TODO.md).

See [`CHANGELOG.md`](../CHANGELOG.md#v3) for the why behind each change.

## Looking ahead

[**v4** (proposed, not approved)](../v4/README.md) specs a full SvelteKit
frontend rewrite, dropping Material Web and reversing
[decision 5](01-overview.md#decisions)'s "no new framework" stance — this
folder remains the actual current, deployed state of the product until
that's built and formally cut.
