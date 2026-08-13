# Specs changelog

## v2.2 — 2026-08-13 (superadmin hierarchy + a real production leak)

Also same version, more post-deploy corrections.

- **Superadmin/admin split** ([04](v2/04-admin-portal.md#0-superadmin-vs-admin),
  [10](v2/10-security.md)). v2 originally shipped with one undifferentiated
  admin role and no way to create a second admin account — a real gap once
  live, not a hypothetical one. `superadmin` adds exactly one capability
  over `admin`: creating/promoting/demoting/suspending other admin
  accounts. Guarded so the last active superadmin can never be
  demoted/suspended.
- **Fixed a live password-hash leak** ([10](v2/10-security.md#the-leak-that-was-found)).
  `GET /api/practitioners/{id}` — public, unauthenticated — was returning
  every practitioner's bcrypt `password_hash`; eight other routes leaked it
  or `anthropic_api_key_encrypted` to authenticated callers. Found while
  testing the superadmin routes (which had the same bug), fixed the same
  day across all nine routes. Recorded in full per the same "write down the
  leak" precedent v1 set.
- Admin dashboard (`/admin`) got a logout button it never had, and an
  already-logged-in visitor to `/login` now redirects straight to their
  dashboard instead of re-prompting for credentials.

## v2.1 — 2026-08-13 (post-deploy fixes)

Same version, no new scope — corrections made after v2 went live at
https://telehealth.devshorepartners.id, tracked here rather than silently
folded into the v2 entry below since the spec was already "finalized" when
these were found.

- **Retired the rest of v1's UI.** `/` used to serve v1's combined SPA
  unauthenticated; it now redirects to `/login`. The SPA's old
  "Practitioner" tab (patient records, consult) called `/api/patients` and
  `/api/consult`, both retired when v2 shipped — deleted rather than left
  broken, along with the now-fully-unused `app/gate.py` and
  `app/patients.py`.
- **Added `POST /api/auth/change-password`** ([08](v2/08-api.md#any-authenticated-role))
  and an account settings page — v1's shared passphrase had nothing to
  rotate; v2's real accounts needed a way to and none existed until this.
- **Clean top-level page routes** ([03](v2/03-website.md)) replacing
  `/static/public/...`-style URLs, which leaked the on-disk directory
  layout into every link a visitor could see or share.
- **Migrated v1's test patient data** into a Pro practitioner's vault by
  hand (one-off script, not a route) so existing POC demo data stayed
  visible after the cutover instead of being silently orphaned.

## v2 — 2026-08-13

Scope expanded from a single-practitioner PoC to the full multi-tenant
product: a public marketing/directory website, an admin portal, a
practitioner portal (basic + pro plans), and a client portal.

**Why:** the PoC proved grounded, cited RAG answers work. The next step is
the product around it — practitioner acquisition (public directory site),
operator tooling (admin), and self-serve practitioner accounts with paid
tiers (Stripe), sized for 10–20 practitioners.

**What's new vs. v1:**
- Public website: about page, practitioner signup, practitioner directory
  (photo, description, specialties, languages, years of experience,
  consultation price — modeled partly on vibly.io's directory), coach detail
  page with a contact form for a client to request an initial call.
- Multi-tenant practitioner accounts on two plans:
  - **Basic** — public profile only.
  - **Pro** — RAG access with the practitioner's own Anthropic API key, a
    separate patient DB, and the ability to create client accounts. No
    library access (library stays admin-curated).
- Admin portal: practitioner CRUD + plan management, library/RAG management
  (all four v1 LLM roles, not a trimmed subset), questionnaire admin, website
  statistics (traffic, per-practitioner profile views, contact forms sent),
  and per-practitioner patient counts.
- Client portal: intake questionnaire, file upload (lab PDFs etc.), and
  wearable integration (Oura, Whoop, Garmin).
- Stripe billing for the practitioner Pro plan. No client-side payments yet.

**Explicitly still out of scope:** mobile app, employer portal, telehealth
video, booking/scheduling, client-to-practitioner payments.

**Superseded:** [v1](v1/README.md) is frozen as-is; nothing in it was edited.

## v1 — Phase 1 PoC

Initial cut. See [v1/README.md](v1/README.md). Not tracked here in detail —
this changelog starts at the v1 → v2 transition.
