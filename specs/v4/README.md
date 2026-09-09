# v4 — SvelteKit frontend rewrite

**Status: built and deployed** (commit `5e0c14f`, 2026-09-02), with two
rounds of post-launch work since — a PM/QA/Clinician review with 42 of 44
findings fixed ([04](04-known-issues.md)), and CI/CD + chunked uploads +
a staged-source review queue + assorted fixes ([05](05-post-launch-additions.md)).
**The formal version cut `specs/README.md` describes — copying forward
every unchanged `v3/` doc, freezing `v3/` as superseded, updating that
file's status table — has not happened.** This folder is the real,
current state of the product; `specs/README.md`'s table and the framing
below (written when this was still a proposal) are stale on that one
point until someone does the mechanical cut. Noted, not silently glossed
over — first flagged in [04](04-known-issues.md)'s process note.

This was originally proposed as a presentation-layer rewrite — SvelteKit
reverses [`v3/01-overview.md`'s decision 5](../v3/01-overview.md#decisions),
which explicitly kept this project framework-free through v1-v3, which is
why it's its own version folder rather than a new doc inside `v3/`, per
`specs/README.md`'s own versioning rule (*"a new version is cut when
there's a change worth auditing: new scope, a reversed decision"*). What
actually shipped went further than presentation-only — see "What this
does not change" below for what's still true and what isn't.

- [**01 · Frontend rewrite: SvelteKit**](01-sveltekit-frontend.md) — the
  architecture: what's kept from the current visual identity vs. what's
  rebuilt, why Material Web is dropped in favor of Svelte-native
  components, the file-based-routing IA mapping, the `load()` data layer,
  the static-adapter deployment (prerendered public portal, client-side
  everything else — no new server process, no VPS memory risk), and a
  phased migration plan.
- [**02 · Open questions and risk ledger**](02-open-questions.md) — the
  tradeoffs, unverified assumptions, and reversible-vs-expensive decisions
  a reviewer needs before saying go.
- [**03 · Visual redesign**](03-visual-redesign.md) — the composition-level
  redesign 01 doesn't attempt: a two-tier surface-weight system (one
  full-treatment panel per screen, everything else quieter) that resolves
  the "keep the gradient" vs. "less cramped" tension directly, applied
  concretely per portal/screen, plus 01's spacing scale actually applied
  to real values instead of just proposed.
- [**04 · Known issues**](04-known-issues.md) — a PM/QA/Clinician-lens
  review of the deployed build: 9 Critical, 12 High, 18 Medium, 5 Low
  findings, 42 fixed same-session.
- [**05 · Post-launch additions**](05-post-launch-additions.md) —
  automatic CI/CD deploy, chunked uploads up to 200 MB, a staged-source
  review queue (upload/paste several sources, ingest all or one at a
  time — builds [`v3/18`](../v3/18-document-ingest-upgrade.md)'s
  never-implemented spec), a multi-panel layout fix, and a display-bug
  fix.

## What this does not change (mostly)

Product scope, information architecture, and the auth model carry forward
from `v3` unchanged — see
[01's "What doesn't change"](01-sveltekit-frontend.md#what-doesnt-change).
**The backend and data model are no longer fully unchanged**: 05 added a
`staged_sources` table and a chunked-upload staging mechanism — real new
backend surface, not just new frontend calling existing routes. Everything
else about 01's original "presentation-layer rewrite" framing still holds.

## Everything else

For anything not covered by 01-05, the current, real state of the product
not superseded by a v4 doc is still accurately described in
[`v3/README.md`](../v3/README.md).
