# 04 · Product rename: Clinic → Functional Health Collab

**Status: spec only, not implemented as part of this pass.** Added
mid-implementation of 01-03; tracked separately since it's an orthogonal,
mechanical change (naming) rather than an IA/UX finding, and touches a
different surface (branding strings, package/service names) than the
audits in 01-03.

## Scope

Every user-visible and machine-facing occurrence of "Clinic" as the
product name becomes "Functional Health Collab". This is a rename only —
no route, IA, or component-structure change implied; where "clinic" is
used as a *generic* word (not the product name) it's unaffected.

**In scope:**

- **Public-facing copy**: `web/src/routes/(public)/+page.svelte:38`,
  `about/+page.svelte:25,32,44`, `account/+page.svelte:29`,
  `join/+page.svelte:49`, `login/+page.svelte:35`,
  `signup/+page.svelte:49` — every `<svelte:head><title>… — Clinic</title>`
  and prose reference becomes "… — Functional Health Collab" /
  "Functional Health Collab connects clients with…".
- **Nav wordmark**: `web/src/lib/components/PublicNav.svelte:34`'s
  `<span class="wordmark">Clinic</span>` — becomes "Functional Health
  Collab" or a suitable short form/lockup if the full name doesn't fit the
  nav's visual space (a design call for whoever implements: consider an
  abbreviated wordmark, e.g. "FHC", paired with a full name in the `<title>`
  tags and footer instead of forcing the full four-word name into the
  same nav slot the single word "Clinic" previously occupied).
- **`AppRail.svelte:38`**'s `aria-label="Clinic home"` → "Functional
  Health Collab home".
- **Admin copy**: `admin/+page.svelte:298,351` — "Teaching Clinic" /
  "teaching Clinic" as a UI verb-phrase becomes "Teaching the library" or
  similar — reads oddly as "Teaching Functional Health Collab" if
  substituted literally; needs a rewrite, not a find-replace, since this
  is the one case where "Clinic" was doing double duty as both the
  product name and a description of the ingest action. **Note**: this
  string lives inside `admin/+page.svelte`, the frozen Library page — the
  [README](README.md)'s exclusion is about layout/composition, not about
  never touching a string inside it; a pure text-content rename doesn't
  violate that freeze.
- **`web/src/app.css:1`**'s file-header comment ("Clinic v4 — tokens
  carried forward…") — cosmetic, update for consistency.
- **Backend**: `app/main.py:1`'s module docstring ("Clinic — FastAPI app
  for the online clinic platform") and `app/main.py:82`'s
  `FastAPI(title="Clinic — Online Clinic Platform", ...)` — the `title=`
  value is user-visible (renders in the auto-generated `/docs` OpenAPI
  page), so it's a real rename target, not just a comment.
- **`app/scraper.py:53`**'s scraper User-Agent string
  (`"ClinicLibraryBot/1.0"`) — visible to any site the web-scraper ingest
  feature fetches from; becomes e.g.
  `"FunctionalHealthCollabLibraryBot/1.0"`.
- **Top-level docs**: `README.md` (title `# Clinic` and prose throughout)
  and `DEPLOY.md` (title `# Clinic — deployment`) — both fully rewritten
  for the new name, not just the headers.
- **Package/service naming**: `web/package.json`'s `"name": "web"` is
  already generic (not "clinic"), so no change needed there. Check
  `DEPLOY.md` and `.github/workflows/deploy.yml` for any systemd service
  name, process name, or directory path literally named `clinic` (e.g. a
  `systemctl` unit like `clinic.service`, referenced in
  `specs/v4/04-known-issues.md`'s deploy-verification note) — **if such a
  service name exists, renaming it is a real deployment-affecting change**
  (requires coordinated systemd unit rename + restart on the actual VPS,
  not just a code change) and should be scoped and executed separately
  from the rest of this rename, with the same care as any other
  production service rename.

**Out of scope / explicitly not touched by this doc:**

- The `clinic_session` cookie name (`app/auth.py:25`) — an internal,
  non-user-visible identifier; renaming it invalidates every existing
  logged-in session on deploy (forces every user to re-log-in). Worth
  doing at some point for naming consistency, but it's a deploy-risk
  decision (a forced mass logout) that belongs with whoever owns the
  deploy, not bundled silently into a branding pass.
- Any database name, table name, or internal variable/function using
  "clinic" as an identifier — pure implementation detail, not user-facing branding.
- The actual domain name / DNS, if the product is deployed under a
  clinic-named domain — a business/ops decision well outside a frontend
  spec's scope, noted here only so it isn't forgotten.

## Open question

The full name "Functional Health Collab" is notably longer than "Clinic"
everywhere it currently appears as a compact wordmark (nav bar, browser
tab favicon-adjacent title, the rail's `aria-label`). Whoever implements
this should decide once, consistently, whether there's a short form (e.g.
"FHC") used in space-constrained UI (nav wordmark, rail) with the full
name reserved for prose, `<title>` tags, and formal contexts (README,
`/docs`) — rather than each implementer picking ad hoc per file.
