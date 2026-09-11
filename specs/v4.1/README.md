# v4.1 — Information architecture, user-type separation, known gaps

**Status: implemented, partially.** 01 and 02 (landing/directory split,
user-type separation) are built. Of 03's 28 findings, all 3 Critical and
5 of 7 High are fixed; 2 High, 11 of 12 Medium, and 5 of 6 Low remain open
(one Low is obsolete — see [03](03-known-issues-and-gaps.md) for the
per-finding status, re-audited 2026-09-11). 04 (the product rename) is
still spec-only, explicitly out of scope of the 01-03 implementation work
per this doc's own original scope note below. This status line was stale
as "spec only" until this same re-audit — [specs/README.md](../README.md)'s
table is corrected alongside it.

Produced from a role-by-role walkthrough of the deployed v4
build (commit `5e0c14f` plus everything merged since, through the library
pagination work) on 2026-09-10, reading every route file in
`web/src/routes/` across all four portals — public, client, practitioner,
admin.

**Trigger**: a direct product call that the current UI, while functionally
shipped ([v4/04](../v4/04-known-issues.md), [v4/05](../v4/05-post-launch-additions.md)),
isn't good enough as a product — not a request for more bug fixes on top
of v4, a request to look at the whole thing again through the eyes of each
person who actually uses it (a prospective client or practitioner hitting
the public site cold, a clinician working the app daily, an admin running
the back office) and name what's actually wrong, concretely.

**One explicit exclusion, held constant across every doc in this folder**:
the admin Library page (`admin/+page.svelte` — Knowledge library tabs,
category strip, search, paginated document grid, ingest dialog) is
**out of scope**. Its layout stays exactly as shipped. Every audit below
was told this up front and did not propose changes to it; where it's
mentioned, it's only as a fixed reference point other screens are compared
against.

- [**01 · Landing page and practitioner directory, split**](01-landing-and-directory-split.md) —
  the root route today is simultaneously the marketing landing page and
  the "browse a practitioner" directory, with the actual pitch content
  stranded on `/about`. Splits them into an information-first landing page
  and a dedicated choose-a-practitioner page, and fixes the broken handoff
  between browsing a practitioner and signing up with one.
- [**02 · User-type separation**](02-user-type-separation.md) — client,
  practitioner, and admin currently share one nav shell and one component
  vocabulary with no visible signal of which you're in beyond the words in
  the sidebar tooltips. A cropped screenshot of any portal is
  indistinguishable from the other two. Proposes a per-role visual system
  built from tokens the app already has, plus fixes to the specific places
  role identity is silently dropped (unused `userLabel`, a duplicate
  "Knowledge" label meaning two different things in two portals, one
  undifferentiated account page for every role).
- [**03 · Known issues and gaps**](03-known-issues-and-gaps.md) — a
  severity-ranked punch list from the four-portal walkthrough: three
  Critical-tier functional bugs found along the way (a logout button that
  doesn't log out, an onboarding checklist that's structurally incapable
  of ever showing "not done," a consult summary that looks saved but
  disappears on reload), plus High/Medium/Low workflow and IA gaps per
  portal.
- [**04 · Product rename: Clinic → Functional Health Collab**](04-product-rename.md) —
  every user-visible and machine-facing occurrence of the product name,
  found and listed; spec only, not implemented as part of 01-03.

## What this does not change

Everything in [v4](../v4/README.md) and, transitively,
[v3](../v3/README.md) carries forward except where a doc in this folder
explicitly says otherwise. This is not a rewrite of the frontend
architecture ([v4/01](../v4/01-sveltekit-frontend.md)) or the token-level
visual identity ([v4/03](../v4/03-visual-redesign.md)'s color/gradient/
spacing values) — 02 reuses those tokens, it doesn't replace them. Backend
routes and the data model are assumed unchanged except where a specific
fix (e.g. the logout endpoint actually being called) requires it.
