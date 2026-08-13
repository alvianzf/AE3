# Clinic — deployment

**Live at https://telehealth.devshorepartners.id**, origin `43.156.136.92`,
behind Cloudflare.

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
| Neo4j | localhost only, heap 512m / pagecache 256m (`/etc/neo4j/neo4j.conf`) |
| Patient vault | `/opt/clinic/data/patients.db` (SQLite) |
| Original files | `/opt/clinic/data/originals/` — one file per source, named by source id |
| Secrets | `/opt/clinic/.env`, mode 600 — Anthropic key, Neo4j password, session secret |

All three services are `enabled`, so they come back after a reboot. Verified: the
app waits for Neo4j's bolt port on cold boot instead of crash-looping, and is
healthy roughly 95 seconds after `reboot` (most of that is the JVM starting).

### Two NGINX settings this app depends on

Both are easy to lose in a rewrite and each breaks a core feature silently:

- `client_max_body_size 25m` — the 1 MB default rejects real PDF sources.
- `proxy_read_timeout 300s` — a consult runs Sonnet, then Opus, then Haiku; the
  60 second default cuts it off mid-answer.

## Memory

1.9 GB total, and Neo4j's JVM is the bulk of it. Steady state leaves roughly
500–700 MB available. It works, but there is no headroom for a second JVM or a
large concurrent load — if the box starts swapping, the first thing to check is
Neo4j's heap.

## Updating (v1, still applies to the library pipeline)

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
