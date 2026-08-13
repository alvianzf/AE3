# 04 · Admin portal

The operator's tool. One admin role for this version — no admin sub-roles,
no permission tiers within admin.

## 1. Practitioner management

| Action | Effect |
|---|---|
| Review queue | List of `pending` practitioners with their submitted profile, approve or reject |
| Approve | `status → approved`; now visible in the public directory |
| Reject | `status → rejected`; the applicant is told, not silently dropped |
| Suspend | `status → suspended`; removed from the directory, portal access blocked, vault untouched |
| Edit plan | Basic ↔ Pro. Downgrading Pro → Basic does not delete the vault — see [09 · Payments](09-payments.md#downgrade) |
| Edit profile | Admin can correct a practitioner's public profile directly (typo fixes, policy violations) |

## 2. Library / RAG management

Everything v1 built, unchanged: ingest sources (file or paste), source cards
with provenance, reliability grading, duplicate detection, full-text reading,
coverage dashboard, graph statistics, audit trail. See
[v1/01-overview.md](../v1/01-overview.md) and [v1/03-ai-team.md](../v1/03-ai-team.md)
for the underlying pipeline — it is not being rebuilt, only continuing to
serve every Pro practitioner's consultations instead of one shared portal's.

The source requirement for this version says "all 4 LLM steps" — this is
shorthand for the four roles named in the original product deck (**Reader,
Indexer, Librarian, Specialist**), not a cut. **Confirmed 2026-08-13:** all
five v1 roles, including **Checker** (independent verification), carry into
v2 unchanged, plus the two on-demand roles (Consolidator, Summariser).
Answers stay independently verified before a practitioner sees them.

## 3. Questionnaire admin

Create, edit, and version intake questionnaires ([02](02-data-model.md)).
Editing a live questionnaire creates a new version rather than mutating the
one clients have already answered against. One questionnaire is marked
`is_active` at a time and is what new client signups receive — this version
does not support per-practitioner custom questionnaires; every practitioner's
new clients get the same active questionnaire.

## 4. Website statistics

| View | Shows |
|---|---|
| Site overview | Total directory views, total contact form submissions, trend over time |
| Per-practitioner | Profile views and contact forms received, for that practitioner |
| Contact forms | List of submissions per practitioner, with status (new/contacted/closed) |

Sourced from `profile_view_events` and `contact_form_submissions` in the core
store ([02](02-data-model.md)).

## 5. Patient counts

Per-practitioner client count, sourced by opening each Pro practitioner's
vault ([02](02-data-model.md#cross-tenant-reads-the-admin-portal-needs)).
Basic practitioners show 0 — they have no vault.
