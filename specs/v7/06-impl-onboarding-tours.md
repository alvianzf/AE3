# v7/06 (implemented) — Onboarding tours, Phase 7

**Status: implemented, all three portals.** The one named exception
to `00-overview.md`'s "no backend changes anticipated" — a small
per-account flag, exactly as that doc called out in advance.

## Backend

- A `tour_completed BOOLEAN NOT NULL DEFAULT FALSE` column, added via
  the same `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` idiom this
  codebase already uses everywhere for a pre-existing table (`admins`/
  `practitioners` in `app/core_store.py`; `clients` in `app/vault.py`,
  since a client's own account lives in its practitioner's per-
  practitioner vault schema, not `core_store` — a genuinely different
  storage location this feature had to account for explicitly).
- `core_store.set_admin_tour_completed()` / `set_practitioner_tour_
  completed()`, `vault.set_client_tour_completed()` — one setter per
  table, same shape as the existing `set_*_password` functions.
- New `POST /api/auth/tour-completed` (`app/auth.py`) — one role-
  dispatching route rather than three near-identical ones, since the
  only difference between them is which store function to call.
- `GET /api/auth/me` now does a **live** lookup of `tour_completed`
  and merges it into the response, rather than adding a second
  endpoint every portal's `+layout.ts` would otherwise need to call.
  Every portal already calls this route on every navigation
  (`get(fetch, '/auth/me')`), so this costs zero new round trips
  anywhere — found while reading each portal's actual `+layout.ts`
  before writing any frontend code, per this spec's own stated norm.

## Frontend

- `web/src/lib/components/Tour.svelte` (new) — a spotlight-style
  guided tour: dims the page, highlights one target element at a time
  (matched by a plain CSS selector, re-measured on resize/scroll —
  `scroll` listened in the capture phase specifically, since a page's
  own internal scroll containers, not just `window`, needed to
  re-trigger a re-measure), a callout with the step's copy and
  Next/Skip. Finishing the last step or clicking Skip both call `POST
  /api/auth/tour-completed` — never a hard gate, always dismissible.

## A real scope correction found before writing any tour content

The tour mounts once, at each portal's `+layout.svelte` — one level
above any single page. A step's target selector is only ever matched
against whatever's currently in the DOM, so a step pointing at
page-specific content (the admin Library page's own "+ Add resources"
button, say — part of this phase's original plan in
`06-interactivity.md`) would have nothing to highlight on every other
page of that portal. Caught before building any tour content, not
after: **every step in all three tours targets an element in the nav
rail itself** (a nav link, or the command-palette search trigger) —
the only things actually guaranteed present regardless of which page
is currently open. Same category of honest scope correction as
`03`'s `Card.svelte` descope: the original plan's one-paragraph
description didn't survive contact with how the component actually
has to work.

## Per-portal content

- **Admin** (4 steps): Dashboard, Library, the search/command-palette
  trigger, Users.
- **Practitioner** (4 steps): Dashboard, Consult ("this is where
  you'll spend most of your time"), Clients, the search trigger.
- **Client** (4 steps, warmer copy, per `05`'s explicit framing that
  onboarding matters most here of the three portals): Dashboard
  ("start here each time"), Questionnaire, Health record (folds in
  the trust/privacy note `06`'s original plan called out — "only you
  and your practitioner can see what's here" — since there's no
  separate page to put it on at this rail-only scope), Files.

## Verification

`npm run check` — 0 errors. 3 new warnings, all the same "initial-
value capture" pattern already present ~9 times elsewhere in this
codebase for the identical reason (the tour's active-on-mount state is
deliberately read once from `data.session` at component init, not
re-derived reactively — re-deriving would flip the tour back on if
`data` ever reloads with a stale `tour_completed` before the user's
own completion write lands).

## What this does not change

- No "Replay tour" entry point built in this pass — `06`'s original
  plan named the command palette as a candidate location, but that
  component is deliberately navigation-only (no non-navigation
  actions) per its own spec, and extending it would be a second scope
  decision this pass didn't make. A small button on each portal's own
  settings/profile surface is the more natural fit for a later follow-
  up — not attempted here.
- No change to any existing auth/session logic beyond `/auth/me`'s
  one additive field.
