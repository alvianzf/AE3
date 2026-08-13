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

| Var | Purpose |
|---|---|
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_PRO` | Billing ([09](09-payments.md)) |
| `VAULT_ENCRYPTION_KEY` | Encrypts `anthropic_api_key_encrypted` at rest ([10](10-security.md)) |
| `OURA_CLIENT_ID/SECRET`, `WHOOP_CLIENT_ID/SECRET`, `GARMIN_CLIENT_ID/SECRET` | OAuth app credentials for the connect flow |

## Runbook additions

- **New practitioner vault** is created automatically on Pro activation
  ([09](09-payments.md)) — no manual step.
- **Deleting a practitioner** (explicit admin action, not a subscription
  lapse) removes their vault file, their `vault-files/` directory, and their
  `core.db` row. Irreversible, same as v1's source deletion — no backups
  exist yet ([10](10-security.md)) to undo it.
- **Backups** are not built for this version. Flagged again here because
  operationally this is where it bites: at 10-20 practitioners, one host
  failure without backups is 10-20 practitioners' clinical data, not one
  demo's.
