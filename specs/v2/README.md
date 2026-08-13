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

## Reading order

Read **01** for scope and the decisions everything else rests on, then
**02** — the store split is what makes tenant isolation and the plan
boundary (Basic vs. Pro) structural rather than promised, same principle v1
used for the library/patient split.

## Status

Spec finalized against the decisions in [01](01-overview.md#decisions);
implementation now in progress, phased. All open items are resolved — see
[04](04-admin-portal.md#2-library--rag-management) and
[07](07-ai-team.md#resolved).
