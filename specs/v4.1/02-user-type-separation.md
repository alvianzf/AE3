# 02 · User-type separation

## The problem, confirmed independently by all three portal audits

Client, practitioner, and admin share one shell component,
`web/src/lib/components/AppRail.svelte`, with only `items` and
`portalLabel` swapped per layout (`(client)/client/+layout.svelte`,
`(practitioner)/practitioner/+layout.svelte:1-14`,
`(admin)/admin/+layout.svelte:1-14`). Same pink/red gradient rail, same
icon-only chrome, same component vocabulary everywhere else in each portal
(`Spotlight`, `Quiet`, `StatTile`, `Button`, `Dialog` render identically
regardless of role). **`portalLabel` is only ever used as an
`aria-label`** (`AppRail.svelte:8,10-11`) — invisible to a sighted user. A
screenshot of any portal, cropped to hide the URL, is indistinguishable
from either of the other two. This was independently flagged as the
top-priority finding by the practitioner, admin, and client portal audits
without prompting — three separate reads of three separate portals landed
on the same root cause.

This directly contradicts the product goal of making it obvious, at a
glance, which kind of user you're looking at — whether that's a
practitioner double-checking they're in the clinician workspace and not
the admin back office, or a support person glancing at a shared screen and
needing to know instantly which portal it is.

## Fix: a per-role accent system, built from tokens the app already has

This is a rebalancing of the existing token system, the same move
[v4/03](../v4/03-visual-redesign.md) made for surface weight — not a new
palette to design or maintain:

- Define three accent variants (`--role-admin`, `--role-practitioner`,
  `--role-client`) as alternate values of the existing `--accent`/
  `--accent-soft`/`--accent-ink` token triad already used throughout
  (`+page.svelte` hero gradients, `Chip tone="accent"`, etc.) — same
  gradient *formula*, shifted hue or weight per role, not three unrelated
  color systems. `AppRail` picks the variant from a `role` prop and scopes
  it as a CSS custom-property override on its own root element, so every
  component nested under a given portal's shell inherits the right accent
  without each one needing role-awareness itself.
- `AppRail`'s rail gradient, active-nav-item indicator, and any
  `.leafmark`/Tier-1 emphasis moments within that portal pick up the
  role's accent automatically.
- **Render `portalLabel` visibly**, not just as an `aria-label` — a small
  fixed label at the top of the rail (`AppRail.svelte:8-11`'s existing
  prop, just also painted on screen). This alone, even before any color
  work, fixes the "which portal is this" problem for anyone who can read.
- **Populate `userLabel` everywhere.** `AppRail.svelte`'s `.foot .who`
  slot exists specifically to show "logged in as X" but is left unset by
  both `(admin)/admin/+layout.svelte:16` and, per the client-portal audit,
  the client layout — the one piece of chrome built for identity context
  is silently unused in at least two of three portals. Pass it from each
  layout's loaded session data.

None of this requires new components or a new design language — `AppRail`
already has the props; they're either unused (`userLabel`) or used in a
way that produces no visible output (`portalLabel`). The accent-variant
work is the only net-new piece, and it's additive to the existing token
set, not a replacement.

## Specific collisions this also resolves

- **Two different "Knowledge" screens, same label, same icon.**
  `(admin)/admin/+layout.svelte`'s nav item `{ href: '/admin', label:
  'Knowledge', icon: 'book' }` and
  `(practitioner)/practitioner/+layout.svelte`'s practitioner nav both use
  the word "Knowledge" for genuinely different screens — admin's is
  browse/ingest the shared library (the frozen Library page), the
  practitioner's `knowledge/+page.svelte` is a per-source trust-weight
  slider over that same library, scoped to their own consults. Same word,
  same icon, one filter-level apart in the app, no role-color to
  disambiguate them today. **Fix**: rename the practitioner's nav item to
  something that names what it actually does — e.g. "Library weights" or
  "Trust levels" — so the two screens read as related-but-distinct instead
  of identically labeled.
- **One undifferentiated account page for every role.**
  `(public)/account/+page.svelte:29-46` is shared across client,
  practitioner, and admin, differentiated only by a plain text line
  (`Signed in as {role}`, line 38) — no role-specific chrome, content, or
  even color. It's also effectively orphaned: `PublicNav.svelte:44`'s
  logged-in CTA routes to each role's dashboard, not `/account`, so this
  page is reachable only by typing the URL directly or via a
  password-reset flow. Once the accent system exists, this page should at
  minimum inherit the visiting role's accent; separately worth deciding
  whether it needs a real, discoverable entry point in each portal's nav
  rather than staying effectively hidden.
- **Auth entry points look identical, and lean client-by-default.** Login
  (`login/+page.svelte:38-47`), client signup
  (`signup/+page.svelte:52-75`), and practitioner application
  (`join/+page.svelte:52-73`) all render as the same single
  `.card-panel`/red-header treatment, differing only in heading text —
  nothing visually signals "you're creating a client account" versus
  "you're applying to become a practitioner." Compounding this,
  `PublicNav.svelte:41-49`'s only logged-out CTA is one prominent "Get
  started" button that routes straight to `/signup` (client-only); "For
  practitioners" is a plain-weight text link with much lower visual
  priority. Nothing in the code documents this as a deliberate
  product bias toward client acquisition — worth either owning it
  explicitly (a real growth decision) or fixing it to present both paths
  at comparable weight, consistent with [01](01-landing-and-directory-split.md)'s
  landing page giving both CTAs equal billing.

## What this doc doesn't cover

Token-level values (the actual hue shift per role, exact gradient stops)
are a design decision for implementation time, not specified numerically
here — this doc fixes the *mechanism* (a role picks up a scoped accent
variant, `portalLabel`/`userLabel` render) and names where role identity
is currently dropped; picking the three actual accent colors is downstream
work, ideally done alongside whoever owns the existing token file so it
stays one coherent palette rather than three bolted-on ones.
