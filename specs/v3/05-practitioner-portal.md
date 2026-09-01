# 05 · Practitioner portal

See also [17 · Full-app redesign](17-full-app-redesign.md) for a PM/UX
walkthrough proposing an `md-dialog` add-client flow, `md-tabs` on
client-detail, and a first-run onboarding checklist.

What a practitioner can do depends entirely on plan. There is no third tier.

## Basic plan

- Manage their own public profile: photo, bio, specialties, languages, years
  of experience, consultation price. This is the same data the directory and
  coach-detail page render ([03](03-website.md)).
- View contact form submissions addressed to them ([03](03-website.md)),
  mark them contacted/closed.
- No RAG access, no patient/client DB — nothing to isolate, no vault exists
  ([02](02-data-model.md)).

## Pro plan

Everything Basic has, plus:

- **RAG access**, using the practitioner's own Anthropic API key
  ([02](02-data-model.md), [07](07-ai-team.md)). The library they query is
  the shared, admin-curated one ([04](04-admin-portal.md#2-library--rag-management))
  — Pro does not get an editable library of their own.
- **A patient DB separate from every other practitioner's** — their vault
  ([02](02-data-model.md)). Client records, consultations, and files
  belonging to one practitioner are not reachable through any code path
  belonging to another.
- **Create and manage their own clients.** A Pro practitioner can add a
  client directly (name, email — the client then completes their own
  signup/questionnaire, [06](06-client-portal.md)), in addition to clients
  who self-register on the website and select this practitioner.
- **No library access.** Same separation v1 drew between the admin-curated
  library and the patient vault: a practitioner can *use* the library
  through the Specialist's retrieval, never edit, grade, or ingest into it.

## Upgrading Basic → Pro

Triggers Stripe checkout ([09](09-payments.md)). On successful subscription,
a vault file is created for that practitioner and `plan` flips to `pro`.
Nothing else about their public profile changes.

## What's explicitly not here

No booking/calendar, no telehealth video, no client-side payments collected
through the portal — all out of scope for this version
([01](01-overview.md)).
