# 10 · Security & privacy

v1 ran on a single shared passphrase and said plainly not to put real
patient data behind it ([v1/07-security.md](../v1/07-security.md)). That
door code cannot carry a multi-tenant product with real client accounts,
real payments, and a real client-facing portal — this version needs actual
authentication, and this doc says so rather than quietly inheriting v1's
posture.

## Accounts and roles

Three roles, each with its own credentials: **admin**, **practitioner**,
**client**. Password hashing (bcrypt), session cookies (signed, not a
server-side session store — `app/auth.py`) scoped to one role — a client's
session cannot call a practitioner route and vice versa, checked
server-side per request, not inferred from which page served the request.

**Revised 2026-08-13:** admin splits into two tiers, `admin` and
`superadmin` — see [04 · Admin portal §0](04-admin-portal.md#0-superadmin-vs-admin)
for what the split actually gates (only admin-account management; every
other admin capability is shared). The session cookie carries `admin_role`
alongside `role`/`id`. Unlike `require_practitioner`/`require_client`,
`require_admin` checks `is_active` against the database on every request
rather than trusting the session claim alone — an admin suspension needs to
take effect immediately, not after a stale 12-hour cookie expires.

## Tenant isolation

The vault-per-practitioner design ([02](02-data-model.md)) is itself a
security control: a bug in one query can leak across rows in a shared table,
it cannot open a different SQLite file it was never given the path to. The
practitioner id used to resolve `data/vaults/<id>.db` must come from the
authenticated session, never from a request parameter — otherwise the
isolation the file split buys is undone by trusting the client to say who
they are.

## Practitioner-supplied Anthropic keys

Stored encrypted (`anthropic_api_key_encrypted`, [02](02-data-model.md)),
decrypted only in-process at call time, never returned by any read endpoint,
never logged. A practitioner rotating their key overwrites, not appends —
one key per practitioner.

## Data handling

- **Three stores**, isolation as described in [02](02-data-model.md).
- **Erasure.** Carries v1's redact-audit-not-delete-it behavior into the
  vault schema unchanged.
- **Client data and the model.** Same as v1: client files and questions are
  sent to Anthropic as prompt content, not used for training, but they do
  leave the host — on Pro, using the *practitioner's* key, so it's the
  practitioner's DPA relationship with Anthropic that covers it, not a
  single platform-wide one. This needs to be stated to practitioners at Pro
  signup, not left implicit.
- **Payments.** Card data never touches our servers — Stripe Checkout only
  ([09](09-payments.md)).

## Not protected (carried or new)

| Missing | Consequence |
|---|---|
| Encryption at rest for vault/core SQLite files | Plaintext on disk, same as v1 |
| Backups | None specified yet — worse here than v1, since real client accounts and payment state now exist |
| Rate limiting on public forms | Contact form and signup are spammable |
| GDPR/consent apparatus | No consent records, retention policy, export, or processor register, despite now holding real client PII |
| Full practitioner account deletion | Admin can suspend a practitioner (removes them from the directory, blocks portal access) but there is no route that deletes the account or its vault outright. Found writing [12 · Verification](12-verification.md)'s test suite: cleanup there can only suspend its own fixtures, not remove them. Deliberate per [09 · Payments](09-payments.md#downgrade)'s "never delete a vault as a side effect" rule for *billing* events — but there is currently no *explicit* deletion path either, for an admin who genuinely wants one gone (e.g. a GDPR erasure request from the practitioner side, not just a client's). |
| No exposed audit trail for a vault | [08 · HTTP API](08-api.md) never lists a route to read a Pro practitioner's own `vault.audit()` — neither the practitioner nor the admin can currently see it through the API, only `verify_v2.py`'s direct-store checks can. v1's admin UI showed a merged library+patient audit; v2 replaced that with a library-only `/api/audit` ([04 · Admin portal](04-admin-portal.md)) and never added the vault-side equivalent back. |

## The leak that was found and fixed {#the-leak-that-was-found}

Worth recording in full, same as v1's equivalent incident
([v1/07-security.md#the-leak-that-was-found](../v1/07-security.md#the-leak-that-was-found)) —
found by chance, not by a dedicated audit, and only in production because
that's where it was tested.

`GET /api/practitioners/{id}` — a **public, unauthenticated** route — was
returning a practitioner's `password_hash` (bcrypt) to any visitor. The
root cause: `core_store`/`vault` read functions legitimately return
`password_hash` because `app/auth.py`'s login and change-password checks
depend on it, but nine different route handlers were passing those dicts
straight through to the HTTP response instead of stripping the field first.
The same bug also exposed `anthropic_api_key_encrypted` (the practitioner's
own encrypted key, readable back to themselves — lower severity, same
cause).

**Fixed:** `_public()`/`_public_list()` in `app/main.py` strip both fields;
applied at every route that returns a practitioner, admin, or client dict —
the public directory and detail routes, practitioner signup, admin's
practitioner/admin management routes, superadmin's admin routes, and
`/api/me/profile`/`/api/me/clients*`. A scripted pass over all nine
previously-affected routes confirmed neither field appears in any response
body.

**Not done:** no equivalent regression test was added to `verify_v2.py`
(unlike v1's leak, which got a permanent `verify.py` assertion). This
version was disposed of as a POC-scope fix rather than a hardened one — see
[12 · Verification](12-verification.md) for what is and isn't covered
there.

## VAULT_ENCRYPTION_KEY must be set explicitly

`app/main.py` generates an ephemeral Fernet key at process start when
`VAULT_ENCRYPTION_KEY` is unset, so local development works without any
setup. In any real deployment this is a trap, not a convenience: every
`anthropic_api_key_encrypted` value becomes permanently undecryptable the
moment the process restarts, silently locking every Pro practitioner out of
consultations until they re-enter their key. Set the env var before the
first practitioner sets a key, not after the first restart reveals the
problem.

## Recommendation

Before any real client or payment data goes through this: finish the auth
model above, add backups (vault files especially — losing one is losing a
practitioner's entire clinical record with no recovery path), rate-limit the
public forms, and get a DPA covering both the platform's own Anthropic usage
and practitioners' individual key usage.
