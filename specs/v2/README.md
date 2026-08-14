# Clinic — specifications (v2 · full product)

Public website + admin portal + practitioner portal + client portal, sized
for 10–20 practitioners. See [`../CHANGELOG.md`](../CHANGELOG.md) for what
changed vs. [v1](../v1/README.md).

| # | Document | Covers |
|---|---|---|
| 01 | [Overview](01-overview.md) | Purpose, actors, scope, and the architecture decisions this version rests on |
| 02 | [Data model](02-data-model.md) | Core store, shared library, per-practitioner vaults |
| 03 | [Website](03-website.md) | About, practitioner signup, directory, coach detail + contact form |
| 04 | [Admin portal](04-admin-portal.md) | Practitioner + plan management, library/RAG, questionnaire admin, stats |
| 05 | [Practitioner portal](05-practitioner-portal.md) | Basic vs. Pro capabilities |
| 06 | [Client portal](06-client-portal.md) | Signup, questionnaire, file upload, wearables |
| 07 | [The AI team](07-ai-team.md) | v1's five roles, whose API key pays for which call |
| 08 | [HTTP API](08-api.md) | Endpoints by app, real per-role auth |
| 09 | [Payments](09-payments.md) | Stripe Pro subscription, webhooks, downgrade behavior |
| 10 | [Security & privacy](10-security.md) | Real auth, tenant isolation, what's still unprotected |
| 11 | [Operations](11-operations.md) | Deployment additions, config, runbook |
| 12 | [Verification](12-verification.md) | v2-specific success criteria and how each is tested |
| 13 | [Known issues](13-known-issues.md) | v2.6 backlog from an independent PM+QA review — all Critical/High findings fixed same-day; email-dependent Medium/Low findings deliberately deferred |

## Reading order

Read **01** for scope and the decisions everything else rests on, then
**02** — the store split is what makes tenant isolation and the plan
boundary (Basic vs. Pro) structural rather than promised, same principle v1
used for the library/patient split.

## Status

| | |
|---|---|
| Live at | https://telehealth.devshorepartners.id |
| Stack | FastAPI · Neo4j · SQLite (core store + one vault per Pro practitioner) · Anthropic · Stripe · vanilla JS |
| Auth | Real per-role accounts — admin (admin/superadmin tiers), practitioner, client — see [10](10-security.md) |
| Verified by | `verify.py` (v1's library guarantees, replayed through `/api/me/consult`) + `verify_v2.py` (12 v2-specific checks) |

Deployed and built against the decisions in [01](01-overview.md#decisions).
All open items are resolved — see
[04](04-admin-portal.md#2-library--rag-management) and
[07](07-ai-team.md#resolved). [08](08-api.md) reflects the routes as they
actually shipped, including the clean-URL page routes, the
account/password-change route, and the superadmin routes — none of which
were in the original spec, all added after initial deploy. See
[`../CHANGELOG.md`](../CHANGELOG.md)'s v2.1/v2.2 entries for the full list
of post-deploy corrections, including a password-hash leak found and fixed
the same day it shipped ([10](10-security.md#the-leak-that-was-found)).

**[13 · Known issues](13-known-issues.md):** a 2026-08-14 PM+QA review found
3 critical, 5 high, 4 medium, and 3 low findings. All Critical and High
findings were fixed and deployed the same day — a suspended practitioner's
access is now actually blocked, the client-signup account-takeover path is
closed, the Pro consultation feature has a working key-entry UI, and four
other broken/missing flows were fixed. Findings tied to email/notifications
remain open (no email system exists in this codebase; building one was
out of scope for that pass) — see [13](13-known-issues.md) for exactly
what's still outstanding.
