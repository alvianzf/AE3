# 11 · Operations

Still sized for **10-20 practitioners** ([v2/11-operations.md](../v2/11-operations.md))
— that constraint is unchanged. What's new in v3 is a build step, ahead of
every prior version's zero-build static-file deploy.

## Topology

Unchanged from v2 — FastAPI app, Neo4j, `data/vaults/`,
`data/vault-files/<practitioner_id>/`, Stripe webhook, wearable OAuth
callbacks, reverse-proxied behind Cloudflare.

## Build step {#build-step}

New this version, from adopting Material Web ([15](15-design-system.md)):

1. `npm ci` — installs `@material/web` and Vite from `package.json`/
   `package-lock.json`, committed to the repo.
2. `npm run build` — Vite bundles each page's component imports and the MD3
   theme into `static/dist/`, which the existing FastAPI static-file mount
   serves exactly as it served hand-written JS/CSS before.
3. This must run **before** `uvicorn`/the app process starts serving
   traffic — `static/dist/` is gitignored (build output, not source), so a
   fresh checkout with no build step has no working front end. The
   deployment pipeline gains one new stage; nothing about the FastAPI
   process itself changes.

Local development: `npm run dev` (Vite dev server with hot reload) alongside
`uvicorn --reload`, same two-process pattern as any FastAPI+bundler setup.

This is the project's first build step and first `npm`/Node.js dependency.
Confirm Node is available on the deploy host and pinned to a version (e.g.
via `.nvmrc`) — nothing in prior versions required this and it's easy to
assume a Python-only host has it.

## Configuration additions over v2

Unchanged — see [v2/11-operations.md](../v2/11-operations.md#configuration-additions-over-v1)
for the full table (`CORE_DB_PATH`, `VAULT_ENCRYPTION_KEY`,
`ADMIN_BOOTSTRAP_*`, Stripe, wearable OAuth vars). Two of those vars now
fail closed instead of silently defaulting in production
([10](10-security.md#fixed-hardcoded-fallback-secrets)) — no new vars, but
`session_secret` and `neo4j_password` (previously undocumented hardcoded
fallbacks in `app/config.py`, not previously listed here as configuration at
all) should now be treated as required-in-production alongside
`VAULT_ENCRYPTION_KEY`.

## Runbook additions

Unchanged from v2, plus: verify the reverse proxy passes the `QUERY` HTTP
method through before relying on it for the endpoints that offer it
([08](08-api.md#http-query-method--experimental-read-endpoints-with-a-filter-body))
— it degrades to `POST` client-side if unsupported, so this is a
performance/caching question, not an availability one, but worth a one-time
check against the actual Cloudflare configuration in use.

## First boot on a fresh deployment

Same three steps as v2, with the build step now first:

1. `npm ci && npm run build` (new).
2. Set `ADMIN_BOOTSTRAP_EMAIL`/`ADMIN_BOOTSTRAP_PASSWORD`,
   `VAULT_ENCRYPTION_KEY`, `session_secret`, `neo4j_password` in `.env`
   *before* starting the app for the first time.
3. Start the app — it creates the admin account automatically.
4. Log in as that admin, then consider removing the bootstrap vars from
   `.env`.
