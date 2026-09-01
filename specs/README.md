# Clinic — specifications

Specs are versioned. Each `vN/` folder is a complete, self-contained, frozen
snapshot — enough on its own to audit what was built, or to rebuild the system
from scratch, at that point in time. Nothing in a released version folder is
edited after the fact; a change becomes a new version.

| Version | Status | Covers |
|---|---|---|
| [v4](v4/README.md) | proposed, not approved | A SvelteKit frontend rewrite — spec only, `v3` is still what's actually built and deployed |
| [v3](v3/README.md) | **current** | v2 plus bounded AI-answer revision, a reachable Summariser, and Material Design 3 |
| [v2](v2/README.md) | superseded | Full product: public website, admin portal, practitioner portal, client portal |
| [v1](v1/README.md) | superseded | Phase 1 PoC: single-passphrase access, one practitioner portal, RAG over a graded library |

See [`CHANGELOG.md`](CHANGELOG.md) for what changed between versions and why.

## Working convention

- Never edit a spec inside a released `vN/` folder. If reality has moved on
  from what's written, that's a signal to cut the next version, not to patch
  the old one.
- A new version is cut when there's a change worth auditing: new scope, a
  reversed decision, a data-model change — not for typo fixes within an
  in-progress version.
- Bump the folder (`v3/`, ...), copy forward the docs that didn't change,
  rewrite the ones that did, and add an entry to `CHANGELOG.md` explaining the
  why.
- This `README.md` always points at the current version.
