# 10 · Security & privacy

v1 ran on a single shared passphrase and said plainly not to put real
patient data behind it ([v1/07-security.md](../v1/07-security.md)). That
door code cannot carry a multi-tenant product with real client accounts,
real payments, and a real client-facing portal — this version needs actual
authentication, and this doc says so rather than quietly inheriting v1's
posture.

## Accounts and roles

Three roles, each with its own credentials: **admin**, **practitioner**,
**client**. Password hashing (bcrypt/argon2, not rolled by hand), session
cookies or JWT scoped to one role — a client's session cannot call a
practitioner route and vice versa, checked server-side per request, not
inferred from which page served the request.

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

## Recommendation

Before any real client or payment data goes through this: finish the auth
model above, add backups (vault files especially — losing one is losing a
practitioner's entire clinical record with no recovery path), rate-limit the
public forms, and get a DPA covering both the platform's own Anthropic usage
and practitioners' individual key usage.
