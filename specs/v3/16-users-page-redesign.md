# 16 · `/admin/users` redesign

Requested directly ("the Users page is weird and stupid, go over it with a
Product Manager and redesign the whole experience") — not part of the
original v3 scope, added alongside it.

**Status: implemented.** `static/admin/users.html`, `src/pages/users.js`,
`static/style.css` (`.tab-bar`/`.tab-btn`), and `static/admin/dashboard.html`
(the "Review" link) all match the redesign below. Verified locally with a
Playwright smoke pass: tab switching, client-side search (including the
empty-state message), the practitioner/admin create dialogs, and the
credentials panel landing under the new row.

One bug found and fixed along the way, not part of the original audit:
`renderPractitioners()`'s empty-state fallback
(`` `<ul class="rows">...</ul>` || empty(...) ``) never actually ran —
a `<ul>` wrapper is truthy even with zero rows inside it — so a
no-results search or filter silently rendered an empty list instead of
"None match this search/filter." Pre-existing (the status-filter version
of this code had the same bug), but search made it far more likely to
hit in practice, so it's fixed alongside this redesign rather than
filed separately.

Acting as PM, this is a walkthrough of `static/admin/users.html` and
`static/admin/dashboard.html` as they actually ship, against
[04 · Admin portal §1](04-admin-portal.md#1-practitioner-management), the
same audit format as [14](14-ux-findings-v2.7.md).

## What's wrong

### U1 — The page is three unrelated tools stacked in one scroll

`/admin/users` renders, top to bottom: a site-wide analytics table, a
practitioner list with an always-open account-creation form inline beneath
it, and (for superadmins) a second, near-identical admin list with its own
always-open creation form. Nothing here shares a task — "how many people
viewed the directory this month," "review this practitioner," and "create
a second admin account" are three different jobs a person opens this page
to do, never two of them at once, but all three compete for the same
vertical scroll. The page's name, "Users," only actually describes two of
the three sections.

### U2 — Site statistics is a duplicate, not content

`#stats-panel` on `/admin/users` is byte-for-byte the same panel — same
"Directory / profile views" / "Contact form submissions" rows, same
`/admin/stats` call — as `/admin/dashboard`'s "Site overview" panel. It
tells the operator nothing about users, practitioners, or admins; it's
leftover surface area, not a considered part of this page. Whoever put it
here had a reason to want stats visible from Users once, but the fix for
"I want to check stats without leaving the flow" is a link to Dashboard,
not a second copy of the same table that can drift from the original.

### U3 — Dashboard's "Review" link doesn't land where it promises

`/admin/dashboard`'s "Pending applications" panel links each entry to
`/admin/users` via a plain `Review` button — no query string, no anchor.
`/admin/users`'s practitioner filter (`#p-filter`) defaults to "All
statuses" and never reads the URL, so an admin who clicks "Review" from a
list of 3 pending applicants lands on a page listing every practitioner
regardless of status and has to re-filter by hand to get back to what they
just clicked on. Same shape of bug as
[14 §P1](14-ux-findings-v2.7.md#p1--critical-start-consultation-on-a-clients-page-doesnt-actually-start-a-consultation-with-that-client):
a link visually promises "take me to X" and instead opens the generic,
unfiltered picker.

### U4 — Creating an account and browsing the list are permanently the same view

The "Add practitioner" form (name, email, password, bio, specialties,
languages, years, price — 8 fields) sits open and visible under the
practitioner list at all times, whether or not anyone's about to use it.
Same for "Add admin" under the admin list. An admin who opens this page to
suspend one practitioner scrolls past a full account-creation form to get
there, every time. Nothing hides the form when it's not in use, and
nothing calls attention to it when it is.

### U5 — No way to find one practitioner by name

The only filter is status (`pending`/`approved`/`rejected`/`suspended`).
At the "10-20 practitioner scale" the code's own comments cite, that's
tolerable; it stops being tolerable as soon as the roster grows past a
screenful, and there's no search box to grow into — it would be a new
control, not a config flip.

## Redesigned page

Same URL (`/admin/users`), same two audiences (admin sees Practitioners
only; superadmin sees both), restructured around "one task in view at a
time":

```
┌─────────────────────────────────────────────────────────┐
│  Practitioners   Admins*                                 │  ← tabs, superadmin only sees "Admins"
├─────────────────────────────────────────────────────────┤
│  [ Search name/email...  ] [ Status: All ▾ ]  [+ Add]    │
├─────────────────────────────────────────────────────────┤
│  Name / email        Status    Plan    Clients  Actions   │
│  ...list...                                                │
└─────────────────────────────────────────────────────────┘
```

- **Tabs, not stacked panels.** "Practitioners" (default) and "Admins"
  (superadmin only — for a plain admin, the tab doesn't render, same
  access rule as today, just expressed as one hidden tab instead of one
  hidden panel). Whichever tab is active owns the full page; the other
  isn't rendered, so there's never a moment where an admin scrolls past
  content they can't act on.
- **Site statistics removed entirely.** Not moved, not collapsed — gone
  from this page. `/admin/dashboard` already owns it (U2). If operators
  want a stats shortcut from Users, that's a plain link to Dashboard, not
  a second live table.
- **Search box** alongside the existing status filter, client-side over
  the already-fetched list (same fan-out `client-count` calls, no new
  endpoint) — matches name or email, case-insensitive. Room to move
  server-side later if the roster outgrows one page of results; not
  needed at today's scale.
- **"+ Add practitioner" / "+ Add admin" opens the creation form**
  (`md-dialog`, since this version already has Material Web available —
  [15](15-design-system.md)) instead of rendering it permanently inline.
  Same fields, same validation, same credentials-reveal-once behavior
  ([14 §A4](14-ux-findings-v2.7.md)) — the dialog closes and the new row
  appears in the list; the one-time credentials panel opens under the new
  row, not in a fixed slot at the page bottom, so it's next to the thing
  it's about.
- **Dashboard's "Review" link carries the filter it promises**:
  `/admin/users?tab=practitioners&status=pending`, and the page reads both
  params on load — the tab and status filter this fixes is real UI state,
  not a new concept.
- **Row actions unchanged** (approve/reject/suspend/reactivate, plan
  toggle, admin role/suspend) — U1–U5 are about layout and navigation, not
  about which actions exist or what they do.

## What's explicitly not changed

- No new permissions or roles — same admin/superadmin split as
  [04 §0](04-admin-portal.md#0-superadmin-vs-admin).
- No new backend endpoints — search is client-side over the existing
  `GET /admin/practitioners` response; the tab/status query params are
  read by the page, not sent to a new route.
- Row-level actions (approve, reject, suspend, plan toggle, admin
  role/suspend) keep their current behavior and confirmation-free,
  immediate-effect design — not in scope for a layout redesign.
