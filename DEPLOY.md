# Clinic — deployment

**Live at https://telehealth.devshorepartners.id**, origin `179.198.198.186`,
behind Cloudflare. (This doc previously said `43.156.136.92` — stale; the
origin moved at some point without this file being updated. Verified
against the live server, 2026-09-09.)

## Automatic deploy (current)

**Pushing to `main` deploys automatically** via
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) — GitHub
Actions builds the SvelteKit frontend, `rsync`s `app/` and the build output
to the server, reinstalls Python deps, and restarts `clinic.service`, gated
behind a `check` job (Python syntax check + `npm run check`) that must pass
first. Auth is a dedicated ed25519 deploy key (repo secret
`DEPLOY_SSH_KEY`, restricted to no-pty/no-forwarding), not a password.
Everything below this section describes what that workflow automates —
kept for manual/emergency use and for understanding what's actually
happening on the server, not the normal path anymore.

## How TLS ended up arranged

The plan was Cloudflare-Flexible (edge TLS, plain HTTP to the origin), but the
zone's SSL/TLS mode is **Full**, so Cloudflare connects to the origin on **443**,
not 80. With nothing listening there the site returned **Cloudflare 521 — web
server is down**, and the nginx access log confirmed it: not a single request from
a Cloudflare IP ever arrived on port 80.

Fixed by giving the origin its own TLS listener:

- NGINX serves **both** 80 and 443, so Flexible and Full both work.
- 443 uses a **self-signed** certificate at `/etc/nginx/origin-tls/` (10-year).
  Cloudflare's *Full* mode accepts it — it encrypts the hop without verifying the
  chain. **Full (strict)** would reject it.
- Net effect: browser↔Cloudflare and Cloudflare↔origin are both encrypted, which
  is better than the Flexible plan, and `COOKIE_SECURE=true` is now set.

To move to Full (strict), replace that certificate with a Cloudflare Origin CA
cert (Dashboard → SSL/TLS → Origin Server) or a real one, keeping the same paths:

```
/etc/nginx/origin-tls/origin.crt
/etc/nginx/origin-tls/origin.key
sudo nginx -t && sudo systemctl reload nginx
```

`certbot --nginx -d telehealth.devshorepartners.id` is the other route, but the
HTTP-01 challenge has to reach the origin through the proxy — grey-cloud the
record for the duration, or use DNS-01 with a Cloudflare API token.

## Cloudflare and API clients

Cloudflare's browser-integrity check answers **error 1010** to requests with an
unrecognised user agent, which is why `verify.py` sets an explicit `User-Agent`.
Anything else scripted against this host needs to do the same.

## Access

**v2 replaces the shared passphrase with real accounts** — see
`app/auth.py` and [`specs/v2/10-security.md`](specs/v2/10-security.md). Three
roles (admin, practitioner, client), each with their own login at
`/static/public/login.html`. `app/gate.py`'s passphrase (`DevshorePartners2026`)
no longer gates anything once v2 is deployed.

- `/api/health` is still deliberately left open so a monitor can check the
  service without a session. Every other route requires the matching
  `require_*` dependency.
- The **first admin account** only exists if `ADMIN_BOOTSTRAP_EMAIL` /
  `ADMIN_BOOTSTRAP_PASSWORD` were set in `.env` *before* the app's first boot
  after this deploy — see "Updating to v2" below. There is no other way to
  create the first admin.

## What runs where

| Piece | Detail |
|---|---|
| App | `/opt/clinic`, venv at `/opt/clinic/.venv`, systemd unit `clinic` |
| Uvicorn | `127.0.0.1:8000`, `--proxy-headers`, `MemoryMax=500M` |
| NGINX | `/etc/nginx/sites-available/clinic` (80 + 443), shared body in `snippets/clinic-proxy.conf` |
| Origin TLS | self-signed, `/etc/nginx/origin-tls/` |
| Real client IP | `/etc/nginx/conf.d/cloudflare-realip.conf` — logs show the visitor, not Cloudflare's edge |
| Neo4j | localhost only, heap 512m / pagecache 256m (`/etc/neo4j/neo4j.conf`) — **needs the APOC plugin** (specs/v5): `POST /api/consolidate`'s entity-merge tool (`app/graph/store.py`'s `merge_entities()`) calls `apoc.merge.relationship`, which doesn't exist on stock Neo4j. Install via `apt-get install neo4j-plugin-apoc` (or drop `apoc.jar` into Neo4j's `plugins/` dir per the version in use) and add `dbms.security.procedures.unrestricted=apoc.*` to `neo4j.conf`, then restart. Without it, ingestion/retrieval/the admin Library work fine — only the "Consolidate" dedup action fails, loudly (`Unknown function 'apoc.merge.relationship'`), not silently |
| Postgres | localhost only, role `postgres`, database `clinic` — core store (`public` schema) + one schema per Pro practitioner's vault (`vault_<id>`). Replaces the old per-file SQLite stores (specs/v6) |
| Original files | `/opt/clinic/data/originals/` — one file per source, named by source id |
| Secrets | `/opt/clinic/.env`, mode 600 — Anthropic key, Neo4j password, session secret |

All three services are `enabled`, so they come back after a reboot. Verified: the
app waits for Neo4j's bolt port on cold boot instead of crash-looping, and is
healthy roughly 95 seconds after `reboot` (most of that is the JVM starting).

### Four NGINX settings this app depends on

Easy to lose in a rewrite and each breaks a core feature silently:

- `client_max_body_size 25m` — the 1 MB default rejects real PDF sources.
  Uploads up to 200 MB are supported without raising this: `app/uploads.py`
  + `web/src/lib/chunkedUpload.ts` split a large file into 4 MiB chunks, so
  no single request needs a body anywhere near 25m.
- `proxy_read_timeout 300s` — a consult runs the Answer Engine through several
  traversal hops, then the Reasoner, then optionally the Checker; the 60
  second default cuts it off mid-answer.
- `proxy_buffering off` — **without this, `/api/me/consult`'s SSE stream is
  silently broken**, not just slow. NGINX's default (`on`) buffers the
  *entire* upstream response before forwarding anything downstream, so no
  event reaches the client until the whole multi-hop consult finishes —
  and since that can legitimately take 100+ seconds, Cloudflare's own edge
  timeout fires first (`524`) with the practitioner seeing nothing at all,
  not even a slow answer. Found live 2026-09-11: the backend was correctly
  streaming per-hop progress the whole time; NGINX just never passed any
  of it through. Every other route here is a normal request/response, so
  turning buffering off doesn't cost anything elsewhere.
- `client_body_timeout` (nginx default: 60s) — chunk size (4 MiB) was picked
  to stay well under this even on a slow connection; if `CHUNK_BYTES` in
  `chunkedUpload.ts` is ever raised, raise this alongside it or a chunk
  upload from a slow connection will time out server-side.

## Postgres (specs/v6 — replaces the old per-file SQLite stores)

**One-time setup on the server**, alongside the existing Neo4j install:

```bash
sudo apt-get install -y postgresql
sudo -u postgres psql -c "ALTER ROLE postgres WITH PASSWORD '<a real generated password>';"
sudo -u postgres createdb -O postgres clinic
```

Add to `/opt/clinic/.env` (alongside the existing Neo4j/Nebius vars):

```
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<the password set above>
POSTGRES_DATABASE=clinic
```

`app/core_store.py`'s `ensure_schema()` and each practitioner's
`app/vault.py`'s `ensure_schema()` create their own tables/schemas on
boot — no separate `CREATE TABLE` step needed beyond the database itself
existing.

**Migrating existing data** (only relevant the first time this cutover
ships to a server that already has `data/core.db` / `data/vaults/*.db`
from before this change):

```bash
cd /opt/clinic
.venv/bin/python scripts/migrate_sqlite_to_postgres.py --dry-run   # see counts first
.venv/bin/python scripts/migrate_sqlite_to_postgres.py             # then actually copy
```

Idempotent (every insert is `ON CONFLICT DO NOTHING`) — safe to re-run if
it's interrupted partway. The old SQLite files are left in place, not
deleted, after a successful migration; remove them manually once the new
data's been spot-checked.

**Isolation note, worth stating plainly since it's a real security
property**: the old design kept each practitioner's clinical data in a
physically separate SQLite file specifically so one practitioner's data
could never leak into a query scoped to another (specs/v1/07-security.md,
"the leak that was found"). This migration preserves that guarantee via
a separate Postgres **schema** per practitioner rather than a separate
**file** — a query against `vault_connection(practitioner_id)` has its
`search_path` set to exactly that practitioner's schema and nothing
enforces cross-schema queries at the app layer, but this is a *weaker*
boundary than separate files/processes: a bug that runs raw SQL with an
attacker-controlled schema-qualifier, or a Postgres-level privilege
misconfiguration, could cross the boundary in a way a wrong file path
couldn't. Worth a real security review before this handles actual patient
data in production, not assumed equivalent to the old guarantee by default.

## Memory

1.9 GB total, and Neo4j's JVM is the bulk of it. Steady state leaves roughly
500–700 MB available. It works, but there is no headroom for a second JVM or a
large concurrent load — if the box starts swapping, the first thing to check is
Neo4j's heap.

## Updating (v1, still applies to the library pipeline)

**Historical record of the v1→v2 cutover — the connection details below
(`ubuntu@43.156.136.92`) are stale, same as this doc's old origin IP
above. Pushing to `main` deploys automatically now; use these manually
only if that pipeline is down, and connect with the current host/user
(`root@179.198.198.186`, or better, the `DEPLOY_SSH_KEY` deploy key) —
not what's written here.**

```bash
# from the project root
scp app/*.py ubuntu@43.156.136.92:/opt/clinic/app/
scp static/* ubuntu@43.156.136.92:/opt/clinic/static/
ssh ubuntu@43.156.136.92 'sudo systemctl restart clinic'
```

`verify.py`'s grounding/citation/grade-threshold checks are unaffected by v2 —
the library pipeline (`app/knowledge.py`, `app/llm.py`'s Reader/Indexer/
Librarian/Specialist/Checker) is unchanged. What v1's `verify.py` can no
longer do post-v2 is drive it through `/api/patients` and `/api/consult` — those
routes are retired; `verify_v2.py` exercises the same guarantees through
`/api/me/consult` instead (see its "carried forward" section), alongside the
nine v2-specific checks.

## Updating to v2

This is a **breaking cutover**, not an incremental update: the shared
passphrase stops working, `/api/patients` and `/api/consult` are gone, and
v1's SPA "practitioner" tab (patient/consult) at `/` will 404 once deployed
— the admin/library tab still works, now behind real login.

```bash
# 1. One-time, BEFORE the first restart — add to /opt/clinic/.env:
#    ADMIN_BOOTSTRAP_EMAIL=<your admin email>
#    ADMIN_BOOTSTRAP_PASSWORD=<a real password — remove this line after first login>
#    VAULT_ENCRYPTION_KEY=<python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
#    PUBLIC_BASE_URL=https://telehealth.devshorepartners.id
#    (Stripe / wearable OAuth vars only if turning those on now — see
#    specs/v2/11-operations.md's config table)

# 2. From the project root:
scp requirements.txt ubuntu@43.156.136.92:/opt/clinic/requirements.txt
ssh ubuntu@43.156.136.92 'sudo -u clinic /opt/clinic/.venv/bin/pip install -r /opt/clinic/requirements.txt'
scp app/*.py ubuntu@43.156.136.92:/opt/clinic/app/
scp -r static/public static/practitioner static/client static/shared.js \
    ubuntu@43.156.136.92:/opt/clinic/static/
ssh ubuntu@43.156.136.92 'sudo systemctl restart clinic'

# 3. Verify
CLINIC_URL=https://telehealth.devshorepartners.id \
ADMIN_BOOTSTRAP_EMAIL=<same as above> ADMIN_BOOTSTRAP_PASSWORD=<same as above> \
ANTHROPIC_API_KEY=<a real key> .venv/bin/python verify_v2.py
```

`/opt/clinic/data/patients.db` (v1's patient data) is orphaned by this
cutover — nothing in v2 reads it, and nothing deletes it either; it's left in
place.

## Logs

```bash
sudo journalctl -u clinic -f          # app
sudo tail -f /var/log/nginx/clinic.error.log
sudo journalctl -u neo4j -n 50
```

## Not production-ready

Deliberately, for a PoC demo: no user accounts, no TLS on the origin, no
backups, no rate limiting, and no separation between the demo's patient data and
anything real. Do not put actual patient information into it.
