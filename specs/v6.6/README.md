# v6.6 — Client and superadmin portal audits, public-page layout fix

**Status: implemented, live-verified in production.** Two structured
"act as a real user" audits (client/patient, then platform operator)
run against the live app, each turning up real functional and honesty
gaps — plus an unrelated layout bug reported directly by a user of this
session.

- [**01 · Client-portal audit**](01-client-portal-gaps.md) — the
  wearables page implied a real vendor data pull when the backend is
  deliberately fixture data (fixed: honest "Coming soon" state); the
  questionnaire ignored its own typed schema and rendered every
  question as a plain textarea (fixed: type-aware inputs, theme
  grouping, progress bar). One finding left open for a product
  decision: a client currently has no visibility at all into what
  their practitioner discussed or decided via the AI consult tool.
- [**02 · Superadmin-portal audit**](02-superadmin-portal-gaps.md) — a
  real Postgres audit trail was being written on every sensitive admin
  action with no way to ever read it back (fixed); admin-account
  management and client-account management existed on the backend with
  zero UI (both fixed); a security-relevant gap found while wiring up
  client suspension — `app/auth.py` didn't actually check the new
  active flag anywhere, so a suspended client could still log in or
  keep an existing session (fixed, same live-check pattern the admin
  role checks already use).
- [**03 · Public-page dead gutters**](03-public-page-layout.md) — the
  navbar and practitioner-directory grid were capped at the same
  78rem reading-width used for actual body text, leaving large dead
  margins on wide screens with nothing narrower of their own to
  justify it. Shipped a fix, then reverted same day at user request —
  the page documents the fix's approach (and a specificity pitfall in
  its first draft) for reuse if this comes back later, but the live
  state is unchanged from before this version.

## What this does not change

No retrieval, ingestion, or AI-team routing logic changed — this
version is UI/UX gap-fixing and one auth-enforcement fix, not a
pipeline change. `v6.5`'s model-routing picture is still current.
