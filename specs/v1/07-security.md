# 07 · Security & privacy

Read this before putting anything real into Clinic. It is a proof of concept, and
several things a clinical system needs are absent by design.

## The access gate

`app/gate.py` puts a **single shared passphrase** in front of the whole application.

This is a **door code, not authentication**. There are no user accounts, no roles,
and no per-user audit. Everyone who knows the phrase has full access to every
patient record and can spend the Anthropic key.

| | |
|---|---|
| Passphrase | `ACCESS_PASSPHRASE` (production: `DevshorePartners2026`) |
| Cookie | `clinic_access`, HttpOnly, SameSite=Lax, `Secure` when `COOKIE_SECURE=true` |
| Cookie value | `HMAC-SHA256(SESSION_SECRET, ACCESS_PASSPHRASE)` — only someone who knows the phrase can produce it |
| Lifetime | 12 hours. Changing `SESSION_SECRET` invalidates every cookie. |
| Comparison | `hmac.compare_digest`, constant time |

### What is gated

Middleware, so coverage does not depend on remembering to decorate a route.

| Path | Unauthenticated |
|---|---|
| `/gate` | open |
| `/api/health` | open, so a monitor can check liveness without the door code |
| `/api/*` | **401** with a JSON detail |
| everything else | the gate page |

Gating only the HTML would leave every `/api` route readable to anyone who guessed a
path. `/static/*` returns the gate page rather than the asset.

## The leak that was found {#the-leak-that-was-found}

Worth recording, because it was invisible and it contradicted the product's central
privacy claim.

The Neo4j audit trail was recording:

```
practitioner · patient created   · "Anna K."
practitioner · question asked    · "Her vitamin D is low and her ferritin is low — …"
```

A patient's name and a clinical question about her, sitting in the knowledge
library — outside the vault the deck says her data never leaves.

**Fixed:** patient-touching events now go to `patients.log()` in SQLite. The library
audit only ever records source events, and only ever names source ids. The
already-leaked rows were purged from production.

**Prevented from returning:** `verify.py` step 7b asserts that no library-store audit
row contains the patient's name, their id, or the question text, and that no
patient-touching action ever appears there. The check was proved to work by
deliberately reintroducing the leak — it fails, then passes once reverted.

## Transport

Cloudflare-proxied, `telehealth.devshorepartners.id` → origin `43.156.136.92`.

The zone's SSL/TLS mode is **Full**, so Cloudflare connects to the origin on 443.
NGINX serves both 80 and 443; 443 uses a **self-signed** origin certificate, which
Full accepts (it encrypts the hop without verifying the chain).

- browser ↔ Cloudflare: TLS, valid certificate
- Cloudflare ↔ origin: TLS, **unverified** certificate
- `COOKIE_SECURE=true`

**Full (strict)** would reject the self-signed certificate. To get there, install a
Cloudflare Origin CA certificate at the same paths ([08](08-operations.md)).

Real client IPs are recovered from `CF-Connecting-IP` over Cloudflare's published
ranges, so logs show the visitor rather than the edge.

## Secrets

| Secret | Where |
|---|---|
| `ANTHROPIC_API_KEY` | `/opt/clinic/.env`, mode 600, owned by `ubuntu` |
| `NEO4J_PASSWORD` | same; Neo4j binds to `127.0.0.1` only |
| `SESSION_SECRET` | same; random per deployment |

`.env` is gitignored. Neo4j's bolt and HTTP ports are not exposed off-host.

## Data handling

- **Two stores.** Knowledge in Neo4j, patients in SQLite. The separation is
  structural and tested ([02](02-data-model.md)).
- **Erasure.** `DELETE /api/patients/{id}` removes the patient, entries, sessions and
  turns, and **redacts** their audit detail while keeping the rows — an erasure
  request should not also erase the evidence that it was honoured.
- **Patient data and the model.** Patient files and questions are sent to the
  Anthropic API as prompt content. They are not used for training, but they do leave
  the host. Any real deployment needs this in its DPA and privacy notice.
- **No backups.** Deleting a source or erasing a patient is irreversible.

## Not protected

Stated plainly so nobody assumes otherwise:

| Missing | Consequence |
|---|---|
| User accounts, roles, per-user audit | Actions are attributed to `admin`/`practitioner`, not a person |
| Rate limiting | Anyone with the phrase can run up API cost |
| Origin certificate validation | The Cloudflare→origin hop is encrypted but unauthenticated |
| CSRF tokens | The gate POST is unprotected; low impact as it only sets the door cookie |
| Encryption at rest | Neo4j and the SQLite file are plaintext on disk |
| GDPR apparatus | No consent records, retention policy, export, or processor register |
| Backups / recovery | None |

## Recommendation

Do not put real patient information into this deployment. It is a demo. If it is to
carry real data, the minimum is: real authentication with roles, Full (strict) TLS,
encryption at rest, rate limiting, backups, and a completed DPA covering the
Anthropic processing.
