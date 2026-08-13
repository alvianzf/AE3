# 11 · Operations

Sized for **10-20 practitioners**. This number is a design constraint, not
a floor to build past — every choice below is the one that needs no new
infrastructure at this scale, not the one that scales furthest.

## Topology

Same shape as v1 ([v1/08-operations.md](../v1/08-operations.md)): FastAPI
app, Neo4j, reverse-proxied behind Cloudflare. What's added:

- `data/vaults/` — up to ~20 SQLite files, each small (one practitioner's
  clients). No connection pooling concerns at this count; a file is opened
  per request and closed, same as v1's single patient DB.
- `data/vault-files/<practitioner_id>/` — uploaded client files, mirrors the
  library's `data/originals/` convention.
- Stripe webhook endpoint, publicly reachable, signature-verified.
- OAuth callback endpoints for Oura/Whoop/Garmin connect
  ([06](06-client-portal.md)) — registered apps with each vendor, even
  though the data pulled after connecting is fixture data for now.

## Configuration additions over v1

| Var | Purpose | Required before first use |
|---|---|---|
| `CORE_DB_PATH`, `VAULTS_PATH`, `VAULT_FILES_PATH`, `PHOTOS_PATH` | New data stores ([02](02-data-model.md)) — sensible relative-path defaults, but set them under `/opt/clinic/data/` in production like v1's `SQLITE_PATH`/`ORIGINALS_PATH` | No — defaults work, just confirm they land under the same data volume as everything else |
| `ADMIN_BOOTSTRAP_EMAIL`, `ADMIN_BOOTSTRAP_PASSWORD` | Creates the first admin account on boot if none exists ([10](10-security.md)) | **Yes** — with no accounts and no signup route for admins, there is no other way to get the first one in |
| `VAULT_ENCRYPTION_KEY` | Encrypts `anthropic_api_key_encrypted` at rest ([10](10-security.md)) | **Yes** — unset, the app generates a throwaway key every process start, so every stored Pro key becomes unreadable on the next restart |
| `PUBLIC_BASE_URL` | Builds Stripe checkout/webhook return URLs and OAuth redirect URIs | **Yes**, once Stripe/wearables are turned on — must be the real public origin, not `localhost` |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_PRO` | Billing ([09](09-payments.md)) | Only if Pro upgrade via Stripe is enabled — the admin plan-override path works without these |
| `OURA_CLIENT_ID/SECRET`, `WHOOP_CLIENT_ID/SECRET`, `GARMIN_CLIENT_ID/SECRET` | OAuth app credentials for the connect flow | Only if wearable connect is enabled |

## Runbook additions

- **New practitioner vault** is created automatically on Pro activation
  ([09](09-payments.md)) — no manual step.
- **There is no route to delete a practitioner outright** in this version —
  only suspend (removes them from the directory, blocks portal access,
  leaves the vault untouched). Found during the [12 ·
  Verification](12-verification.md) pass; noted as a gap in
  [10 · Security](10-security.md), not fixed here. Until it exists, a
  practitioner who wants to leave the platform has their account suspended,
  not erased.
- **Backups** are not built for this version. Flagged again here because
  operationally this is where it bites: at 10-20 practitioners, one host
  failure without backups is 10-20 practitioners' clinical data, not one
  demo's.

## First boot on a fresh deployment

1. Set `ADMIN_BOOTSTRAP_EMAIL`/`ADMIN_BOOTSTRAP_PASSWORD` and
   `VAULT_ENCRYPTION_KEY` in `.env` *before* starting the app for the first
   time.
2. Start the app — it creates the admin account automatically.
3. Log in as that admin, then consider removing the bootstrap vars from
   `.env` (per [10](10-security.md), they're a one-time bootstrap, not a
   standing credential worth leaving configured).
