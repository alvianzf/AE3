# 08 · Operations

Deployment topology, configuration, and the runbook. The narrative of how the
current TLS arrangement came about is in [`../../DEPLOY.md`](../../DEPLOY.md); this is the
reference.

## Topology

```
browser ──TLS──▶ Cloudflare ──TLS(:443, self-signed)──▶ NGINX ──▶ uvicorn
                  (proxied)                              │        127.0.0.1:8000
                                                         │             │
                                              /static (no-store)       ├─▶ Neo4j 127.0.0.1:7687
                                                                       ├─▶ SQLite /opt/clinic/data
                                                                       └─▶ api.anthropic.com
```

| Piece | Detail |
|---|---|
| Host | Ubuntu 24.04, 2 vCPU, 1.9 GB RAM, 40 GB disk, `43.156.136.92` |
| App | `/opt/clinic`, venv `/opt/clinic/.venv`, systemd unit `clinic` |
| Uvicorn | `127.0.0.1:8000`, `--proxy-headers --forwarded-allow-ips=127.0.0.1`, `MemoryMax=500M` |
| NGINX | `sites-available/clinic` (80 + 443), shared body in `snippets/clinic-proxy.conf` |
| Neo4j | 2026.06.0 Community, `127.0.0.1` only, heap 512m, pagecache 256m |
| Python | 3.12 on the server, 3.14 locally — both fine |

All three units are `enabled` and survive a reboot.

## Two NGINX settings this app depends on

Both are easy to lose in a rewrite and each breaks a core feature **silently**:

| Setting | Without it |
|---|---|
| `client_max_body_size 25m` | The 1 MB default rejects real PDF sources |
| `proxy_read_timeout 300s` | A consult runs Sonnet → Opus → Haiku; the 60 s default cuts it off mid-answer |

## Static assets must not be cached

`/static/` is served `Cache-Control: no-store, must-revalidate` **and** referenced
with a `?v=N` query string that is **bumped on every deploy**.

This is not belt-and-braces for its own sake. Cloudflare caches `.js`/`.css` by
extension for four hours; a stale `app.js` ran against a changed API shape and
rendered "the library is empty" ([06](06-frontend.md)). Verify after deploying:

```bash
curl -s -b cookies -A "Mozilla/5.0" \
  https://telehealth.devshorepartners.id/static/app.js?v=N | shasum -a 256
# must equal: shasum -a 256 static/app.js
# response header should read cf-cache-status: BYPASS
```

## Configuration

`/opt/clinic/.env`, mode 600. Defaults live in `app/config.py`.

| Key | Default | Notes |
|---|---|---|
| `NEO4J_URI` / `_USER` / `_PASSWORD` / `_DATABASE` | `bolt://127.0.0.1:7687`, `neo4j` | |
| `SQLITE_PATH` | `data/patients.db` | The patient vault |
| `ORIGINALS_PATH` | `data/originals` | Uploaded files kept byte-for-byte; created on first write. Grows with the library — the only store here that holds arbitrary uploaded bytes |
| `ANTHROPIC_API_KEY` | — | Required |
| `READER_MODEL` | `claude-haiku-4-5` | |
| `LIBRARIAN_MODEL` | `claude-sonnet-5` | **Not Haiku** — see [03](03-ai-team.md#why-sonnet-and-not-haiku) |
| `ANSWER_MODEL` | `claude-opus-5` | |
| `CHECKER_MODEL` | `claude-haiku-4-5` | |
| `ACCESS_PASSPHRASE` | `DevshorePartners2026` | |
| `SESSION_SECRET` | dev placeholder | Set a random value; changing it logs everyone out |
| `COOKIE_SECURE` | `false` | `true` in production |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 1200 / 150 | |
| `MIN_GRADE` | 7 | Default threshold |
| `MAX_SOURCES` | 100 | |
| `MAX_PASSAGES` | 120 | The binding prompt bound |
| `MIN_SHARED_CONCEPTS` | 2 | |

## Memory

1.9 GB total; the JVM is the bulk of it. Steady state leaves roughly 400–700 MB
available. It works, with no headroom for a second JVM or heavy concurrency. If the
box starts swapping, check Neo4j's heap first.

`MemoryMax=500M` on the app unit exists so a runaway worker cannot push Neo4j out.

## Cold boot

Verified by reboot: healthy about **95 seconds** after `reboot`, most of it the JVM
starting.

The app **waits** for Neo4j's bolt port (30 attempts, 2 s apart) rather than exiting.
Before that it crash-looped three times per boot and served 502s. `NRestarts` should
be `0` after a clean boot — a non-zero value means something else is wrong.

## Deploying

```bash
# code only — never touch data
scp app/*.py    ubuntu@43.156.136.92:/opt/clinic/app/
scp static/*    ubuntu@43.156.136.92:/opt/clinic/static/
ssh ubuntu@43.156.136.92 'sudo systemctl restart clinic'
```

Then, in order:

1. bump `?v=N` in `index.html` **before** copying, and confirm served hashes match
2. `curl /api/health` — all three probes green
3. `CLINIC_URL=https://telehealth.devshorepartners.id .venv/bin/python verify.py`
4. if the schema gained fields, `POST /api/relink` to connect anything unlinked

Schema changes are additive and applied at startup; existing data keeps working
([02](02-data-model.md#migration-behaviour)).

## Moving to Full (strict) TLS

Replace the self-signed certificate with a Cloudflare Origin CA certificate
(Dashboard → SSL/TLS → Origin Server), keeping the paths:

```
/etc/nginx/origin-tls/origin.crt
/etc/nginx/origin-tls/origin.key
sudo nginx -t && sudo systemctl reload nginx
```

`certbot --nginx -d telehealth.devshorepartners.id` also works, but HTTP-01 must
reach the origin through the proxy — grey-cloud the record for the duration, or use
DNS-01 with a Cloudflare API token.

## Runbook

| Symptom | Check |
|---|---|
| Cloudflare **521** | Is 443 listening? `sudo ss -tlnp \| grep 443`. Full mode uses 443, not 80. |
| Cloudflare **1010** | A scripted client without a recognisable `User-Agent`. |
| "Library is empty" but `/api/sources` has rows | Stale cached `app.js`. Compare served vs local hashes; bump `?v=`. |
| **502** just after boot | Normal for ~90 s while the JVM starts. Persisting → `journalctl -u clinic`. |
| Consult times out at 60 s | `proxy_read_timeout` lost from the NGINX config. |
| PDF upload rejected | `client_max_body_size` lost from the NGINX config. |
| Answers ignore a low-graded source at grade 1 | `LIBRARIAN_MODEL` reverted to Haiku. |
| Traversal never links anything | Sources unlinked (`GET /api/graph`) — run `POST /api/relink`. |

```bash
sudo journalctl -u clinic -f
sudo tail -f /var/log/nginx/clinic.error.log
sudo journalctl -u neo4j -n 50
```

## Not production-ready

No backups, no rate limiting, no observability, no encryption at rest, and a shared
door code instead of authentication. See [07](07-security.md).
