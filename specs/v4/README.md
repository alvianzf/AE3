# v4 — SvelteKit frontend rewrite (proposed, not approved)

**Status: proposal.** Unlike `v1`/`v2`/`v3`, this folder is not yet a frozen
record of something built — it's the spec for something requested but not
yet greenlit. [`specs/README.md`](../README.md)'s versioning rule is what
put this in its own folder rather than a new numbered doc inside `v3/`:
*"a new version is cut when there's a change worth auditing: new scope, a
reversed decision"* — SvelteKit reverses
[`v3/01-overview.md`'s decision 5](../v3/01-overview.md#decisions), which
explicitly kept this project framework-free through v1-v3. That's a
version boundary, not an addendum.

Once (if) this direction is approved and actually built, formally cutting
this version the way `specs/README.md` describes — copying forward every
`v3/` doc that doesn't change, freezing `v3/` as superseded — is a
mechanical step to do at that point, not before. Right now this folder
holds exactly the two documents that are the actual proposal:

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

## What this does not change

Product scope, information architecture (with one named exception), the
backend, the data model, and the API contract all carry forward from `v3`
unchanged — see [01's "What doesn't change"](01-sveltekit-frontend.md#what-doesnt-change).
This is a presentation-layer rewrite, same framing `v3` itself used for
adopting Material Web.

## Everything else

Not copied into this folder yet, per the "proposal, not a cut version"
status above — read the current, real state of the product at
[`v3/README.md`](../v3/README.md).
