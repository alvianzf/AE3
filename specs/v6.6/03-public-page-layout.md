# v6.6/03 — Public-page dead gutters (shipped, then reverted)

**Status: reverted at user request.** The final state of this version
is the original layout, unchanged from before this entry.

`.container` (`app.css`, `max-width: 78rem; margin: 0 auto`) is shared
across the whole app. On pages that also have their own narrower
reading-width class on the same element (hero copy, pitch/pillars text,
login/signup/join form cards), that local class already wins. Two spots
relied on `.container` alone with nothing narrower of its own — the
public navbar's inner row, and the practitioner-directory search/
results grid — so on anything wider than 1248px, the 78rem cap read as
large dead margins on both sides.

Shipped a fix: a new `.container-wide` class (same centering/padding as
`.container`, no width cap) swapped into just those two spots. Verified
locally at 1920px and on production after deploy — navbar and directory
went edge-to-edge, forms/hero/pitch text unaffected.

**Reverted same day, on request** — the navbar and directory are back
to the original `.container`-capped layout. `.container-wide` was
removed from `app.css`; `PublicNav.svelte` and
`practitioners/+page.svelte` are back to plain `.container`.

One implementation note worth keeping even though the change itself
was reverted: the first attempt at the fix used a blanket
`:global(.public-shell .container) { max-width: 100% }` override
scoped to the public layout, intending to leave elements with their own
narrower class untouched. It didn't — that override and a page's own
local class (e.g. `.about`) land at equal CSS specificity, so which one
won came down to unpredictable build-time source order, and in practice
it also stretched the landing page's pitch/pillars text to full width.
The `.container-wide` class-swap approach that replaced it had no such
ambiguity. If a similar full-width treatment is wanted again later,
that's the pattern to reuse — not the global override.
