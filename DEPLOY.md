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

The whole app sits behind a single shared passphrase — see `app/gate.py`. This is
a door code, **not** authentication: there are no user accounts, and everyone who
knows the phrase has full access to every patient record.

- Passphrase: `DevshorePartners2026` (`ACCESS_PASSPHRASE` in `/opt/clinic/.env`)
- Cookie lasts 12 hours; changing `SESSION_SECRET` logs everyone out.
- `/api/health` is deliberately left open so a monitor can check the service
  without holding the door code. Every other route is gated, API included.

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

## Updating

```bash
# from the project root
scp app/*.py ubuntu@43.156.136.92:/opt/clinic/app/
scp static/* ubuntu@43.156.136.92:/opt/clinic/static/
ssh ubuntu@43.156.136.92 'sudo systemctl restart clinic'
```

Verify end to end against the deployment:

```bash
CLINIC_URL=https://telehealth.devshorepartners.id .venv/bin/python verify.py
```

It ingests its own fixtures and removes them again on the way out, so it can be
run against the live instance without leaving debris in the library. Two caveats:

- Step 9 is skipped against a remote target — it talks to the store directly and
  would otherwise test your laptop's database instead of the server's.
- The test patient is left behind on purpose (deleting patients is not exposed in
  the API). Remove it before a demo if you want a clean patient list.

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
