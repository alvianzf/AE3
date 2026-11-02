# v6.8 — Library folders, and a real citation deep-link

**Status: implemented (both `01` and `02`).**

Two requests, both about making the knowledge library a navigable place
rather than a flat, graded list:

- [**01 · Library folders**](01-library-folders.md) — admins organize
  uploaded sources into folders and subfolders. The Reader suggests a
  location and a name at ingest time (same mechanism it already uses to
  suggest topics); the admin's placement is always final, and can be
  changed later.
- [**02 · Citation deep-link**](02-citation-deep-link.md) — clicking a
  `[K1]`-style citation on a generated answer currently just scrolls to
  that entry in the same page's Sources accordion
  (`practitioner/consult/+page.svelte`'s `onAnswerClick`). It instead
  opens the library, in a new tab, at that exact document and passage —
  which requires a real routed document-detail page, since today's
  viewers (admin Library, `practitioner/knowledge`) are both client-side
  dialogs with no URL of their own.

## Baseline — already shipped, not re-specced here

Two pieces of this request already exist:

- **Admin/superadmin CRUD on admins, practitioners, and clients** —
  `v6.6`'s audit found admin/client account management built on the
  backend with no UI and fixed that; `app/main.py`'s `/api/superadmin/
  admins*` and `/api/admin/practitioners*`/`/api/admin/clients*` routes,
  `web/src/routes/(admin)/admin/users/+page.svelte`. Superadmin-only
  where the action is sensitive (role changes, admin suspension —
  `auth.require_superadmin`); plain admin for practitioner/client
  approval and suspension (`auth.require_admin`). Nothing in this
  version changes that.
- **Practitioners viewing library documents** — `v6.7/03` gave
  `practitioner/knowledge/+page.svelte` a full source viewer (extracted
  text, or the original PDF inline), mirroring the admin Library page's
  existing one. `01` below adds folders on top of this listing; `02`
  below is what actually needs a new, routed page instead of this
  existing dialog-in-a-list-page shape.

## What this does not change

No retrieval, ingestion-pipeline, or AI-team routing logic. The Reader's
new suggestion in `01` is an additive field on its existing structured
call, not a new role or a new call.
