# v7/02 (implemented, partial) — Landing page, Phase 1

**Status: implemented — icon pillars + scroll-triggered reveals only.**
The product-glimpse decision (`02-public-site.md`'s static screenshot
vs. interactive-demo choice) and the social-proof section remain
explicitly deferred — both are real content decisions for the user,
not styling ones, same as the spec said.

## What shipped

- Each of the landing page's 4 pillar cards now carries an icon
  (`book`/`file`/`check`/`settings`, matched to its own claim — "trained
  on your library," "every claim cited," "independent check," "you set
  the bar") instead of being title+body text alone.
- A new `web/src/lib/actions/reveal.ts` — a generic
  `IntersectionObserver`-backed Svelte action, extending the app's
  existing `liftIn` keyframe (`app.css`) from "plays once on mount" to
  "plays once as the element actually scrolls into view." Respects
  `prefers-reduced-motion` explicitly (reveals immediately rather than
  relying on the animation-duration override alone, since an element
  that's never observed intersecting would otherwise stay invisible
  forever for a reduced-motion user who doesn't scroll that far).
  Applied to the pitch paragraph, the pillar grid (staggered via a
  `--reveal-delay` custom property, 60ms per card), and the closing
  dual-CTA row.
- **Deliberately not applied to the "trust" panel** — it already has
  its own mount-time entrance via the shared `.card-panel` class
  (`app.css`). Found in review before shipping: a `liftIn` keyframe
  with `animation-fill-mode: both` finishes at `opacity: 1` on mount
  regardless of scroll position, which would have both defeated a
  second scroll-gated `opacity: 0` start state layered on top and
  looked actively broken (the section visible before the pillars above
  it had even revealed). Left with its existing animation only.

## Verification

`npm run check` — 0 errors, warning count back at the pre-phase
baseline after fixing one real issue found along the way: Svelte's
compile-time CSS pruner flagged `.pitch.revealed`/etc. as unused,
since the `revealed` class is added dynamically by the action (not
present in any markup Svelte can see at compile time) — fixed with
`:global(.revealed)` on the dynamic portion of each selector.

## What this does not change

No change to the hero section (always above the fold — a scroll
reveal has no practical effect there, left alone), `Seo.svelte`'s
output, the JSON-LD schema, or any other public route. The product-
glimpse and social-proof additions from `02-public-site.md` remain
unbuilt pending the user's content decision.
