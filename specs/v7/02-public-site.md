# v7/02 — Public site redesign

Covers `web/src/routes/(public)/*`: `/` (landing), `/practitioners`,
`/join`, `/login`, `/signup`, `/account`, `/coach`. (`/about` is
already a pure redirect to `/` per `specs/v4.1/01` — stays that way,
not a page to redesign.)

## Landing page (`/+page.svelte`)

Current structure (read in full): a gradient hero (headline + two
CTAs), a one-paragraph pitch, a 4-item pillar grid (plain text cards,
no icons), a single "trust" panel (the AI-team explanation + 4 chips),
and a closing dual-CTA row. All content, no product visuals — no
screenshot, no demo, no data. Entrance animation exists
(`liftIn`/`fadeIn`, staggered via each section's own `<style>`) but
nothing is interactive; a visitor can only scroll and click a CTA.

Proposed changes:

- **Pillars get icons** — `Icon.svelte` already has a broad library
  (book, chart, bell, user-card, lock, etc.); the 4 pillars
  ("Trained on what you teach it", "Every claim is cited", etc.) each
  get one, turning a 4-paragraph text block into a scannable grid —
  directly serves "not confusing."
- **A real product glimpse**, not just copy. Two options, named here
  for the user to pick between when this page's implementation is
  scheduled (not decided in this spec, since it's a real content/
  scope decision, not a styling one):
  1. A static annotated screenshot of the consult page's cited-answer
     view (the product's actual strongest visual — citations, grading,
     the checker's verification badge) with callouts.
  2. A lightweight interactive demo: a pre-scripted, client-side-only
     fake "ask a question → see a cited answer stream in" sequence
     (no real backend call — canned data), triggered on scroll-into-
     view or a "See it work" button. Directly serves the "interactive"
     priority and is a much stronger first impression than static
     copy, at real but bounded build cost (one new component, no
     backend change).
- **Micro-animations on scroll**, not just on initial mount — today's
  `liftIn`/`fadeIn` only fire once, on page load, so a visitor who
  scrolls past the fold sees every section already fully rendered
  with no motion at all. An `IntersectionObserver`-driven reveal (each
  section fades/lifts in as it enters the viewport) is the single
  highest-leverage "feels modern" change available for the lowest
  risk — no new dependency (native browser API), reuses the exact
  animations already defined in `app.css`.
- **Social proof section**, currently absent entirely — no testimonial,
  no practitioner count, no "as seen in." Out of scope to fabricate
  content for; flagged as a real content gap the user should decide
  whether to fill (with real data, once there's a real practitioner
  base to cite) before or after the visual redesign ships.

## `/practitioners` (the directory)

Not read in detail for this pass — flagged for its own focused look
when scheduled, since it's a search/filter/grid page (a different
pattern class than the landing page's static sections) and deserves
the same "read the actual current code first" treatment the design-
system spec establishes as the norm, not an assumption carried over
from the landing page's structure.

## `/join`, `/login`, `/signup`

Conversion-critical forms — the two moments ("become a practitioner,"
"log in") where friction most directly costs the product a user.
Proposed direction for all three, pending their own detailed read:

- Inline field validation (not just submit-time errors) using the
  existing `TextField.svelte` — a real UX gap on any current form that
  only surfaces a validation error after a failed submit.
- A visible multi-step progress indicator for `/join` if its
  application flow is more than one screen (needs confirming against
  the actual current implementation before committing to this).
- Consistent use of the new `Skeleton.svelte` (from `01`) for the
  post-submit "processing" state rather than a bare disabled button.

## `PublicNav.svelte`

- Already handles the real logged-in/logged-out bug fix (`specs/v4.1`)
  correctly — kept as-is functionally.
- Visual refresh to match `01`'s updated spacing/type scale.
- Consider a command-palette trigger (`06`) in the public nav too —
  lower priority than the portals (a public visitor has far fewer
  actions to jump between), but worth a quick "Search" affordance
  that at minimum jumps to `/practitioners`' own search.

## What this does not change

- No new routes, no new backend endpoints for the landing page's
  product-glimpse option unless the interactive-demo direction is
  chosen and that demo later needs more than canned client-side data
  (not anticipated).
- `Seo.svelte`, the JSON-LD organization schema, and `sitemap.xml`/
  `robots.txt`/`llms.txt` (specs/v6.7) are unaffected — this is a
  visual/interaction redesign, not an SEO/GEO change.
