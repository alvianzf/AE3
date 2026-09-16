# v6.7 — SEO/GEO, practitioner-owned questionnaires, portal UX batch

**Status: implemented, live-verified in production.** Same week as
`v6.6`'s audits, a run of direct feature/UX requests: making the public
site discoverable (by search engines and AI answer engines alike),
letting practitioners own their own intake questionnaire instead of
sharing one global admin default, and a batch of portal polish
(notification badges, full-width layouts, a library document viewer for
practitioners, more useful dashboards, icon consistency).

- [**01 · SEO and GEO**](01-seo-geo.md) — meta/OG/Twitter tags,
  JSON-LD, a branded OG image, `sitemap.xml`, `robots.txt` explicitly
  naming AI crawlers, `llms.txt`. Includes a same-day bug found and
  fixed: the new root-level static files were being served as the SPA
  shell instead of their real content, since `app/main.py`'s
  `_WEB_ROOT_FILES` allowlist didn't know about them yet.
- [**02 · Practitioner-owned questionnaires**](02-practitioner-questionnaires.md)
  — `questionnaires.practitioner_id` (NULL = admin default) scopes the
  "one active" invariant per-owner instead of globally; explicit
  activate/deactivate; a new practitioner-facing builder; practitioners
  can view (not edit) the site default. Includes a security-relevant
  finding fixed in review: the library-viewer's auth gate (`03`) was
  initially too permissive.
- [**03 · Portal UX batch**](03-portal-ux.md) — notification badges on
  the practitioner nav and Clients list; the practitioner and client
  portals dropping their `.container` width cap (public pages
  untouched); practitioners gaining a real library-source viewer; more
  meaningful dashboard tiles on all three portals; icons extended past
  admin to practitioner and client action buttons.

## What this does not change

No retrieval, ingestion, or AI-team routing logic changed. `v6.6`'s
audits and their fixes stand as shipped; this version is new feature
work and portal polish on top, not a revision of that one.
