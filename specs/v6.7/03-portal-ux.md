# v6.7/03 — Notification badges, full-width portals, library viewer, dashboards, icons

**Status: implemented, live-verified in production.** A batch of direct,
mostly independent UX requests, shipped together (`v6.7/02`'s
practitioner-nav changes overlap with the notification-badge work below,
so they went out in the same PR).

## Notification badges

`AppRail.svelte`'s `NavItem` gained an optional `badge?: number`,
rendered as a small numeric pill on the icon. Wired to counts the
backend already tracked but never surfaced in the nav:
`GET /api/me/notifications`'s `unviewed_intake` on the practitioner
Clients link, `new_contacts` on Contacts. Both already clear on
interaction — `unviewed_intake` via `vault.mark_intake_viewed` (called
when a practitioner opens a client's intake tab), `new_contacts` via the
existing contact-status-to-`handled` transition — no new clearing logic
needed, just a new place to display the existing count.

Also added: a per-client "new intake" marker (a small superscript dot)
directly on the Clients list, next to whichever client's most recent
questionnaire response hasn't been viewed yet
(`vault.list_clients`'s new `has_unviewed_intake`, an `EXISTS` subquery
mirroring `count_unviewed_intake`'s own logic).

## Full-width practitioner and client portals

Direct request: remove the `.container` 78rem width cap from all
dashboards/menus in the practitioner, admin, and client portals — admin
already had no cap (`v6.6`-era comment explained why); practitioner and
client both did, via `class:container`/`class="container"` on their
layout's `<main>`. Removed from both. Public marketing pages are
explicitly untouched, per the same request and consistent with the
`v6.6/03` gutter-fix-then-revert on those pages specifically.

(A `/code-review` pass flagged this width-cap removal as a regression
against the layout's own prior comment explaining why the cap existed —
correct description of the diff, but the removal was the explicit
request, not a bug, so left as shipped.)

## Practitioner library viewer

Practitioners can now view full library source content (extracted text,
or the original PDF inline) from the Library-weights page, not just
adjust a source's weight — mirrors the admin Library page's existing
viewer (`viewDoc`, the same `Dialog`/iframe/pre-wrap-text pattern)
exactly. Backend gate and the Pro-only tightening found in review are
covered in `v6.7/02`. `store.catalogue()` (Neo4j) also gained
`original_name` in its `RETURN` clause — needed so the practitioner
viewer can tell a PDF-backed source from a text-only one, same as the
admin listing already could.

## Dashboards: meaningful metrics and quick actions

- **Admin**: `core_store.site_stats()` gained `new_contacts`,
  `pending_practitioners`, `approved_practitioners` (previously just
  `total_views`/`total_contacts`). The dashboard replaced a raw
  key-value dump with named `StatTile`s that link to the relevant page
  (pending applications → Users, new contacts → Users) — any stat not
  explicitly tiled still renders generically, so a future addition to
  `site_stats()` doesn't need a matching frontend change to show up.
- **Practitioner**: added a `Clients` count tile (the data — `data.clients`
  — was already loaded for the onboarding checklist, just never
  surfaced as its own tile). The rest of the dashboard (onboarding
  checklist, recent contacts, recent consult history) was already
  reasonably built and is unchanged.
- **Client**: added a `Health record` tile — that feature (`v6.5`) had
  no dashboard entry point at all until now. Also dropped a dead
  `/me/wearables` fetch left over from the wearables "Coming soon"
  change (`v6.6/01`) — the tile is a fixed string now, the connections
  list was never read.

## Icons

Action buttons across all three portals (not just admin, extended this
session — `v6.6/03`'s admin-only icon pass covered Users/Questionnaires)
now lead with an `Icon.svelte` glyph, matching the icon-leading-button
style: practitioner Clients (Add/Remove), Contacts (Mark handled), and
client Files (Upload) and Record (Add to my record). `Icon.svelte`
already carried `check`/`x`/`plus`/`pause`/`play`/`edit` from the
earlier admin pass.

## Verification

`npm run check` clean, `python3 -m py_compile` clean on every touched
backend file. Reviewed via `/code-review` before shipping alongside
`v6.7/02` — see that document for both findings fixed in that pass.
