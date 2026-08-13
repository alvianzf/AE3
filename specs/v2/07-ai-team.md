# 07 · The AI team

The five roles are unchanged from v1 ([v1/03-ai-team.md](../v1/03-ai-team.md)):
Reader, Indexer, Librarian, Specialist, Checker, plus the on-demand
Consolidator and Summariser. What changes in v2 is **whose API key pays for
which call**, because there are now many practitioners instead of one
shared portal.

## Whose key, which call

| Call | When | Key used |
|---|---|---|
| Reader, Indexer | Ingesting a source into the shared library | Admin's platform key — this is library curation, an admin operation, not any one practitioner's |
| Consolidator | Tidying the shared concept index | Admin's platform key |
| Librarian, Specialist, Checker | A Pro practitioner's consultation | **That practitioner's own key** ([02](02-data-model.md)) |
| Summariser | Saving a consultation summary to a client's record | That practitioner's own key — it's part of the same consultation |

The split follows who caused the cost: ingesting a source benefits every
practitioner and is an admin decision (what enters the library, what grade
it gets), so the platform pays. Answering one practitioner's question about
one of their clients is that practitioner's cost, paid with the key they
supplied at Pro upgrade.

A Basic practitioner never triggers any of these calls — no RAG access
means no key is ever requested from them ([05](05-practitioner-portal.md)).

## Everything else is v1, unchanged

Model choices, prompt contracts, the no-match refusal path, the reasoning
behind Sonnet over Haiku for the Librarian, the Checker's specific-claim
requirement — none of it changes with multi-tenancy. See
[v1/03-ai-team.md](../v1/03-ai-team.md) for the full detail; it is not
repeated here to avoid two documents drifting out of sync on the same
behavior.

## Resolved

The source requirement names "all 4 LLM steps" for the admin portal's
library management — shorthand for Reader + Indexer + Librarian + Specialist,
the four roles named in the original product deck, before v1 added Checker
during the build. **Confirmed 2026-08-13:** Checker (and the two on-demand
roles, Consolidator and Summariser) carry into v2 unchanged, alongside those
four. See [04 · Admin portal](04-admin-portal.md#2-library--rag-management).
