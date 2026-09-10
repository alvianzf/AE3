# 01 · Landing page and practitioner directory, split

## The problem

`web/src/routes/(public)/+page.svelte` is the site root and does two
unrelated jobs on one route: it's the entry point a cold visitor lands on
*and* the practitioner search/filter/grid ("Find a practitioner",
`+page.svelte:38,42-77`). There is no product information, value prop, or
credibility content anywhere on `/` — a visitor who has never heard of
this product is dropped straight into a search UI for a thing they don't
yet know they want.

The actual pitch — "An AI assistant practitioners can put their name
behind," the four-pillar explanation, the "one accountable AI team" trust
panel — exists, but it lives on `/about` (`about/+page.svelte:30-77`),
reachable only via a secondary nav link (`PublicNav.svelte:7-11` lists
`Directory, About, For practitioners` — browse before information). Every
piece of copy in the app treats `/` as "the directory," not "the landing
page": `join/submitted/+page.svelte:13`'s only exit link is "Back to the
directory" → `/`.

This is backwards for a product whose visitors are, by definition, people
who don't yet know if this is for them. Directory-first only works once
someone already trusts the premise; nothing upstream of the grid currently
establishes that trust.

## The split

**`/` becomes the landing page — information first.** Content: the pitch
currently on `/about` (hero, the four-pillar explanation, the trust panel)
becomes the page. Two clear, equal-weight CTAs below the pitch, not one
biased toward clients the way the nav currently is (see
[02 §Auth entry points](02-user-type-separation.md#auth-entry-points-look-identical-and-lean-client-by-default)):
"Find a practitioner" → `/practitioners`, and "I'm a practitioner" →
`/join`. No search box, no grid, no live data fetch on this route — it's
static marketing content, which also sidesteps the `prerender = true` /
client-side-refresh interaction the current `+page.svelte:15-18` has to
manage for live practitioner data (`+page.ts:3`) — the new landing page
has no live data to go stale.

**`/practitioners` (new route) becomes the directory.** Everything that's
in today's `+page.svelte` — hero band, search, specialty filter, grid,
the prerender-then-refresh pattern for practitioner data — moves here
unchanged in mechanism, just relocated. This is the page someone reaches
after they've decided they want to look, not the page everyone lands on
by default.

**`/about` retires, folded into the new `/`.** Keeping a separate `/about`
that duplicates the landing page's pitch content produces two pages
saying the same thing; that's worse than one page saying it well. If
there's a genuine case for a deeper "how it works" page beyond what fits
on the landing page, that's new content, not the current `/about` kept
around — flagged as an open call for whoever scopes the actual page copy,
not decided here. Redirect `/about` → `/` either way so the URL doesn't
404 for anyone who bookmarked or shared it.

**Nav order flips**: `PublicNav.svelte:7-11`'s items become `Home` (or no
explicit link — logo already goes there), `Find a practitioner`, `For
practitioners` — information is where you land, not a link you have to
find first.

## Fixing the handoff this split would otherwise leave broken

Splitting landing from directory doesn't fix the fact that going from
"I found my practitioner" to "I signed up with them" is currently a dead
handoff:

- **`coach/[id]/+page.svelte:54-60`** (a practitioner's profile page) has
  exactly one CTA: a contact-message form. There is no "Sign up with this
  practitioner" action. A visitor who browsed to this page and decided
  "yes, this one" has to separately navigate to `/signup` and re-pick the
  same person from a bare `<select>` (`signup/+page.svelte:60-65`), losing
  the photo/bio/specialty context that made them choose in the first
  place. **Fix**: add a primary "Sign up with {name}" CTA on the profile
  page that routes to `/signup?practitioner={id}`, with the signup form
  pre-selecting that practitioner from the query param instead of
  defaulting to an empty picker.
- **`signup/+page.svelte:26`** filters the practitioner picker to
  `p.plan === 'pro'` only, silently, client-side. `/practitioners` (the
  directory, all practitioners) has no such filter. A practitioner a
  visitor found and liked on the directory can simply not appear on
  signup, with zero explanation. **Fix**: either apply the same pro-only
  filter on the directory itself (so what you can browse and what you can
  sign up with are the same set), or, if non-pro practitioners are
  supposed to be browsable-but-not-signup-able for a real product reason,
  say so on their profile page rather than letting them vanish silently
  downstream.
- **`signup/+page.svelte:56-58`** — when zero pro-plan practitioners exist,
  the whole form is replaced by one line of static text with no alternate
  path. **Fix**: at minimum a link back to `/practitioners` (browse
  non-pro options, if the product allows it) or a waitlist/contact
  capture — not a dead end.

## Minor data-honesty fixes worth carrying along

- `coach/[id]/+page.svelte:47` renders `p.years_experience ?? 0` and an
  empty languages list as `'Language not listed'` — the years default
  renders as real data ("0 years experience") rather than an omitted-field
  state. Render "Experience not listed" the same way languages already
  does, instead of a misleading `0`.
- `join/+page.svelte:14-15` defaults `years`/`price` to `'0'` with no
  placeholder distinguishing "not set" from "actually zero." Same fix.
