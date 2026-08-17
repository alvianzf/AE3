# 10 · Security & privacy

Carries forward from v2 ([v2/10-security.md](../v2/10-security.md))
unchanged except for two fixes and one clarification found by the v3
architect review ([CHANGELOG](../CHANGELOG.md#v3)).

## Accounts, roles, tenant isolation, practitioner-supplied keys, data handling

Unchanged from v2 — see [v2/10-security.md](../v2/10-security.md) for the
full detail (role-scoped sessions, vault-per-practitioner isolation,
encrypted-at-rest Anthropic keys, redact-not-delete erasure).

## Fixed: hardcoded fallback secrets

`app/config.py` shipped `session_secret` and `neo4j_password` with insecure
hardcoded default values that took effect **silently** if the corresponding
env var was merely unset — the same failure shape already documented for
`VAULT_ENCRYPTION_KEY` below, but not itself flagged until this review. Both
now fail loudly instead: the app refuses to start in a non-development
environment (`ENV=production`) if either is unset, rather than falling back
to a value that ships in every checkout of this repository.

## VAULT_ENCRYPTION_KEY must be set explicitly

Unchanged from v2 — still generates an ephemeral key at process start when
unset, still a trap in production (every stored Pro key becomes
undecryptable on restart), still documented rather than auto-fixed, since
there is no safe automatic behavior here (the app cannot know the
previously-used key to re-derive it). Set it before the first practitioner
sets a key.

## Clarification: retrieval stays deterministic

Recorded here because the v3 AI-team review ([07](07-ai-team.md))
specifically considered and rejected giving agents more autonomy to call
each other, and the security reasoning belongs in this document, not just
the changelog: retrieval (`knowledge.traverse`) is plain Python, not an LLM
call, and stays that way. This matters for prompt-injection blast radius —
the Reader ingests raw, unsanitized source text (only length-truncated) into
a prompt, so a malicious source could in principle try to influence the
Reader's own output (e.g. an inflated suggested grade). Today that has low
consequence because grades are admin-overridable and no downstream role
re-derives trust from the Reader's prose. If retrieval were ever made
agent-directed instead of deterministic, that same injected text would have
a path to influence *what gets retrieved*, not just one role's own metadata
suggestion — this is the concrete reason retrieval must stay out of the
agent layer, not just a general preference for simplicity.

## Not protected (carried forward)

Unchanged from v2 — see [v2/10-security.md](../v2/10-security.md#not-protected-carried-or-new)
for the full table (no encryption at rest for SQLite files, no backups, no
rate limiting on public forms, no GDPR apparatus, no practitioner-deletion
route, no exposed vault audit trail).

## The leak that was found and fixed

Unchanged from v2 — see
[v2/10-security.md#the-leak-that-was-found](../v2/10-security.md#the-leak-that-was-found).

## Recommendation

Unchanged from v2's recommendation, plus: confirm the reverse proxy passes
the new `QUERY` HTTP method through unmodified before relying on it in
production ([08](08-api.md#http-query-method--experimental-read-endpoints-with-a-filter-body)) —
an intermediary that rejects or mangles an unrecognized method fails closed
for those endpoints, which is a correctness/availability question, not a
data-exposure one, but should be verified rather than assumed.
