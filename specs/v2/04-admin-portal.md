# 04 · Admin portal

The operator's tool. **Revised 2026-08-13:** this originally shipped as one
admin role with no sub-roles or permission tiers. A two-tier hierarchy
replaced that after deploy — see [§0](#0-superadmin-vs-admin) — because
there was no way to create a second admin account otherwise.

## 0. Superadmin vs. admin

| | admin | superadmin |
|---|---|---|
| Practitioner management (§1) | ✓ | ✓ |
| Library / RAG management (§2) | ✓ | ✓ |
| Questionnaire admin (§3) | ✓ | ✓ |
| Website statistics (§4) | ✓ | ✓ |
| Create / promote / demote / suspend other admin accounts | ✗ | ✓ |

Every admin account carries a `role` of `admin` or `superadmin`
([02](02-data-model.md), [10](10-security.md)). The distinction is narrow on
purpose: a superadmin isn't a generally more privileged operator, it's
specifically the one who can grow or shrink the set of admin accounts. At
least one active superadmin always exists — `set_admin_role` and
`set_admin_active` both refuse to demote or suspend the last one, so the
system can never lock itself out of having someone who can create more
admins. The very first admin account (via `ADMIN_BOOTSTRAP_EMAIL`/
`ADMIN_BOOTSTRAP_PASSWORD`, [11](11-operations.md)) is always created as
superadmin, for the same reason.

## 1. Practitioner management

Lives at `/admin/users` — split into its own page from `/admin`'s
knowledge-library dashboard ([08](08-api.md)), since the two have nothing
to do with each other beyond both being admin-only. Available to both
admin and superadmin.

| Action | Effect |
|---|---|
| Add directly | Admin creates a practitioner (name, email, password, profile fields) and it's `approved` immediately — no pending review, since the admin is already vouching for it. Distinct from public signup, which always starts `pending`. |
| Review queue | List of `pending` practitioners with their submitted profile, approve or reject |
| Approve | `status → approved`; now visible in the public directory. Also reactivates a `suspended` or `rejected` practitioner — there's no separate "reactivate," approving from any prior status works. |
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
