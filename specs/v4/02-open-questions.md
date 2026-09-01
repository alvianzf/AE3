# 02 · Open questions and risk ledger

Companion to [01](01-sveltekit-frontend.md) — the tradeoffs and unresolved
calls a decision-maker needs before greenlighting this, gathered in one
place instead of buried in prose. Nothing here blocks writing the spec;
everything here blocks *building* it.

## Decisions this spec made that are reversible, cheaply, if wrong

- **nginx edge-split vs. SvelteKit-internal API proxy** — [01 §Process
  topology](01-sveltekit-frontend.md#process-topology) recommends the
  former. If the internal-proxy approach turns out simpler to operate in
  practice, switching is an nginx config + one `hooks.server.ts` change,
  not a rearchitecture.
- **Drop `@material/web` entirely vs. keep it for 1-2 stubborn components**
  — [01 §Component strategy](01-sveltekit-frontend.md#component-strategy-drop-material-web-not-svelte-native)
  argues for a full drop. If a specific component (the datatable's sort
  affordance, say) turns out meaningfully harder to build accessibly
  from scratch than expected, keeping just that one MD3 component is a
  contained exception, not a reason to keep the whole library.

## Decisions this spec made that are expensive to reverse

- **adapter-node over static-adapter.** This was given, not derived — the
  user confirmed adapter-node specifically. Worth restating plainly since
  it's the single most consequential technical choice in this document:
  static-adapter would have meant *zero* production deployment risk (same
  "sync files, FastAPI serves them" shape as today, per
  [v3/11](../v3/11-operations.md#build-step)'s existing build step) at the
  cost of losing SSR (auth-guard redirects happen client-side again, same
  flash-then-redirect behavior as today; `load()` functions still work but
  run in the browser, so the cookie-forwarding problem in
  [01](01-sveltekit-frontend.md#data-layer-load-functions-against-the-unchanged-fastapi-api)
  disappears entirely — the browser already attaches the cookie). **If the
  VPS memory math in [01 §Deployment](01-sveltekit-frontend.md#what-the-vps-actually-has-today)
  turns out tighter in practice than estimated, revisiting static-adapter
  instead of resizing the VPS is the fallback**, not a dead end — worth
  keeping in mind as a release valve, not raising it to relitigate a
  decision already made.

## Unverified assumptions, stated so they get checked before they get relied on

1. **Node SvelteKit adapter-node memory footprint under this app's actual
   `load()` fan-out is estimated (60-100MB idle, 150-300MB under load),
   not measured.** A throwaway load test (a handful of concurrent
   `load()`-driven page requests against a real deployment on a
   memory-constrained box, or even just `docker run --memory=300m` locally
   against a built adapter-node output) would replace this estimate with a
   number before it's load-bearing for a production capacity decision.
2. **The exact nginx `location` block precedence for a path-based
   incremental cutover** (§Migration plan, step 2-3 in
   [01](01-sveltekit-frontend.md#migrationcutover-plan)) needs to be
   checked against the live `clinic-proxy.conf` snippet on the VPS, not
   assumed from this document's example block — nginx `location` matching
   has well-known surprises (regex vs. prefix precedence, `=` exact-match
   ordering) that are easy to get subtly wrong in a way that silently
   serves the wrong app for one path rather than erroring loudly.
3. **Auth-guard SSR-redirect behavior against every one of `app/auth.py`'s
   real role-check paths** (`require_admin`, `require_superadmin`,
   `require_pro_practitioner`, the plain-authenticated-any-role check) —
   [01](01-sveltekit-frontend.md#information-architecture-file-based-routing-over-the-existing-four-portals)
   asserts this is "strictly better" than today's client-side check, which
   is true in principle (SSR redirect vs. flash-then-redirect) but hasn't
   been verified against every specific 401 vs. 403 vs. redirect-to-login
   distinction those FastAPI dependencies actually make.
4. **Whether Cloudflare's edge caching or any WAF rule interacts
   differently with a Node-rendered HTML response than with FastAPI's
   current static-file responses** — untested. `DEPLOY.md` already
   documents one Cloudflare-specific gotcha this app hit before (the
   browser-integrity check's error 1010 on an unrecognized User-Agent,
   why `verify.py` sets one explicitly) — worth treating "Cloudflare might
   have another opinion about this" as a category of risk to check for,
   not assuming SvelteKit's default response headers are equivalent to
   FastAPI's `StaticFiles` mount in Cloudflare's eyes.

## Cost/effort not estimated here, on purpose

This document doesn't attempt a time/story-point estimate for the actual
rewrite (~24 pages, a new component library, a new deployment pipeline,
a phased cutover) — that's an implementation-planning exercise for once
this direction is approved, not part of "write the spec for it." Flagging
its absence explicitly rather than implying the architecture decisions
above are the hard part; for a rewrite this size, the component-by-
component and page-by-page execution is very likely the larger cost.
