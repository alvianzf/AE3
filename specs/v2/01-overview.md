# 01 · Overview

## Purpose

Clinic grows from a single-practitioner RAG proof of concept into a
multi-tenant platform: a public website that lists hormonal-health
practitioners and lets clients reach out to them, an admin portal that runs
the business and curates the shared knowledge library, a practitioner portal
with a paid tier for AI-assisted consultations, and a client portal for
intake and data collection.

Sized for **10–20 practitioners** at launch. This is not a scale target to
design past — it shapes every build-vs-buy and multi-tenancy decision in this
version.

## Actors

| Actor | Uses | Responsible for |
|---|---|---|
| **Admin** (Clinic operator) | Admin portal | Practitioner accounts and plans, the shared knowledge library, questionnaire design, site-wide statistics |
| **Practitioner** | Practitioner portal, listed on the website | Their public profile; on Pro, their own patient DB and AI-assisted consultations |
| **Client** (a practitioner's patient) | Client portal, public website | Finding a practitioner, requesting a first call, completing intake, submitting records |

Client was explicitly out of scope in v1 ("Clinic never speaks to a
patient"). That changes here: the client portal is new, and clients now have
direct product surface.

## The four applications

| # | App | Covers |
|---|---|---|
| 1 | [Website](03-website.md) | About page, practitioner signup, practitioner directory, coach detail + contact page |
| 2 | [Admin portal](04-admin-portal.md) | Practitioner + plan management, library/RAG management, questionnaire admin, statistics |
| 3 | [Practitioner portal](05-practitioner-portal.md) | Profile (Basic), RAG + patient DB + client management (Pro) |
| 4 | [Client portal](06-client-portal.md) | Intake questionnaire, file upload, wearable integration |

## In scope

- Public marketing/directory website with practitioner profiles modeled
  partly on vibly.io's directory pattern (photo, description, specialties,
  languages, years of experience, consultation price), and a contact form on
  each coach's detail page for a client to request an initial call.
- Practitioner self-signup, gated by admin approval.
- Two practitioner plans:
  - **Basic** — public profile only.
  - **Pro** — RAG access using the practitioner's own Anthropic API key, a
    patient DB separate from every other practitioner's, and the ability to
    create and manage their own clients. Pro does **not** get library
    access — the library stays admin-curated, same separation principle as
    v1's vault split.
- Admin-run knowledge library and RAG pipeline, carried forward from v1: all
  four LLM roles (Reader, Indexer, Librarian, Specialist — Checker if it
  remains in scope for v2, confirm against v1's five-role breakdown before
  reusing the "four LLM steps" phrasing from the source requirement).
- Questionnaire administration: admin defines the intake questionnaire(s)
  clients fill out.
- Client portal: initial questionnaire, file upload (e.g. lab work PDFs),
  and integration with Oura, Whoop, and Garmin.
- Statistics: website traffic on the admin home page, per-practitioner
  profile views, contact forms sent per practitioner, and patient counts per
  practitioner.
- Stripe billing for the practitioner Pro plan subscription.

## Out of scope — deliberately

| Not built | Why |
|---|---|
| **Mobile app** | Explicitly excluded for this version. |
| **Employer portal** | Explicitly excluded for this version. |
| **Telehealth / video** | Explicitly excluded for this version. |
| **Booking / scheduling** | Explicitly excluded for this version. Initial contact is a form, not a calendar. |
| **Client-to-practitioner payments** | Only practitioner→Clinic billing (Stripe, Pro plan) exists in this version. |

## Decisions

Resolved directly with the product owner on 2026-08-13:

1. **Client signup.** Regular self-service signup (email/password) on the
   public website — a client is not required to be invited by a practitioner
   first. See [06](06-client-portal.md).
2. **Multi-tenancy and data isolation.** Recommendation adopted: **one SQLite
   file per Pro practitioner** (`data/vaults/<practitioner_id>.db`), the same
   "separate store is the structural guarantee" principle v1 used for
   patients vs. library, just repeated per tenant instead of once globally.
   At 10-20 tenants this needs no new infrastructure (no Postgres, no
   row-level security to get right), and deleting or exporting one
   practitioner's data is a file operation, not a filtered query that could
   be gotten wrong. Practitioner identity, plan, and public-profile data live
   in one shared central store — that data isn't clinical and is meant to be
   queried across tenants (directory listing, admin stats). See
   [02](02-data-model.md).
3. **Practitioner signup approval.** Admin review queue — a new signup is
   `pending` until an admin approves it; only then does the profile appear
   in the public directory. See [04](04-admin-portal.md).
4. **Wearable integration depth.** OAuth connect flow is real (Oura, Whoop,
   Garmin), but the data pulled after connecting is **dummy/fixture data**
   for this version, not a live vendor API call. This is stated explicitly
   wherever it applies so it isn't mistaken for a finished integration later.
   See [06](06-client-portal.md).
5. **Stack continuity.** v2 keeps v1's stack: FastAPI · Neo4j · SQLite ·
   Anthropic · vanilla JS. No new framework introduced for the public website
   or the additional portals.

## Status

In progress. This overview is agreed; [02](02-data-model.md) onward are being
written against the decisions above.
