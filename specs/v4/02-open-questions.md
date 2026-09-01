# 02 · Open questions and risk ledger

Companion to [01](01-sveltekit-frontend.md) — the tradeoffs and unresolved
calls a decision-maker needs before greenlighting this, gathered in one
place instead of buried in prose. Nothing here blocks writing the spec;
everything here blocks *building* it.

**Revision note:** [01](01-sveltekit-frontend.md) originally specced
adapter-node (SSR, a new Node process in production); revised to the
static adapter with per-route prerendering after the memory math below
made the tradeoff explicit. This file has been updated to match — the
items below describe the *current* (static-adapter) plan's risks, not the
adapter-node version's.

## Decisions this spec made that are reversible, cheaply, if wrong

- **Static adapter now, adapter-node later if a specific need justifies
  it.** SvelteKit's adapter is a swappable build target, not a rewrite —
  if a specific route later needs true SSR (better crawl freshness on the
  public portal, say, if prerendered-at-build-time content turns out to go
  stale in practice), switching that one route's adapter back is a
  contained change, not a redo of [01](01-sveltekit-frontend.md)'s
  component/IA work. This is the fallback direction if the static-adapter
  bet turns out wrong, not a dead end.
- **nginx edge-split vs. app-internal API proxy** — moot under the static
  adapter (FastAPI serves everything, there's no second process to split
  traffic between), but would resurface as a live decision if adapter-node
  is ever adopted for a route per the point above.
- **Drop `@material/web` entirely vs. keep it for 1-2 stubborn components**
  — [01 §Component strategy](01-sveltekit-frontend.md#component-strategy-drop-material-web-not-svelte-native)
  argues for a full drop. If a specific component (the datatable's sort
  affordance, say) turns out meaningfully harder to build accessibly
  from scratch than expected, keeping just that one MD3 component is a
  contained exception, not a reason to keep the whole library.

## Decisions this spec made that are expensive to reverse

- **Prerendering the public portal at build time, not runtime.** If the
  public portal's content (practitioner directory listings, specifically)
  turns out to change often enough that a build-time snapshot goes visibly
  stale between deploys, the fix isn't a config flip — it's either standing
  up on-demand rendering for just those routes (functionally reintroducing
  a server process, the exact thing this revision removed) or adding a
  rebuild-and-redeploy trigger on practitioner-roster changes (new
  operational machinery, [11 §Operations](../v3/11-operations.md) doesn't
  have an equivalent today). Worth a real answer before building, not
  discovering in production — see the unverified assumption below.

## Unverified assumptions, stated so they get checked before they get relied on

1. **How often the public portal's content actually changes** — directly
   decides whether build-time prerendering is even the right call (see the
   expensive-to-reverse item above). `specs/v3/04-admin-portal.md` and
   `06-client-portal.md` describe practitioner approval/suspension and
   profile edits as admin/practitioner-initiated, not high-frequency, but
   this hasn't been checked against real usage patterns — "prerender the
   public portal" assumes new-practitioner-goes-live and profile-edit
   events are rare enough that a rebuild-per-deploy cadence keeps the
   directory acceptably fresh, not stale.
2. **Auth-guard client-side-redirect behavior against every one of
   `app/auth.py`'s real role-check paths** (`require_admin`,
   `require_superadmin`, `require_pro_practitioner`, the
   plain-authenticated-any-role check) —
   [01](01-sveltekit-frontend.md#information-architecture-file-based-routing-over-the-existing-four-portals)
   describes the improvement this buys honestly (blocks render until the
   check resolves, no flash of protected content) but hasn't verified the
   redirect target/message is correct for every specific 401 vs. 403
   distinction those FastAPI dependencies actually make, including a
   suspended practitioner or a role that changed mid-session.
3. **Whether Cloudflare's edge caching treats SvelteKit's prerendered
   static HTML any differently than FastAPI's current `StaticFiles`
   responses** — likely equivalent (both are plain HTTP responses with
   standard headers) but untested. `DEPLOY.md` already documents one
   Cloudflare-specific gotcha this app hit before (the browser-integrity
   check's error 1010 on an unrecognized User-Agent, why `verify.py` sets
   one explicitly) — worth treating "Cloudflare might have another
   opinion" as a category to check, not assumed away.

## Cost/effort not estimated here, on purpose

This document doesn't attempt a time/story-point estimate for the actual
rewrite (~24 pages, a new component library, a new deployment pipeline,
a phased cutover) — that's an implementation-planning exercise for once
this direction is approved, not part of "write the spec for it." Flagging
its absence explicitly rather than implying the architecture decisions
above are the hard part; for a rewrite this size, the component-by-
component and page-by-page execution is very likely the larger cost.
