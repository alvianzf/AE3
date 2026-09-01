# 15 · Design system: Material Design 3

New this version. Every prior version ([v1/06-frontend.md](../v1/06-frontend.md))
was three files, no framework, no build step. v3 adopts
[Material Web](https://github.com/material-components/material-web)
(`@material/web`), Google's official MD3 web-component library, for the
component layer — the first real dependency and the first build step this
project has had.

This is a presentation-layer change. No information architecture changes:
the numbered-sequence layout, the two-portal/four-portal structure, and
every flow described in [03](03-website.md)/[04](04-admin-portal.md)/
[05](05-practitioner-portal.md)/[06](06-client-portal.md) carry forward
unchanged — those documents are not rewritten for v3. What changes is what
each screen is built out of.

## Why full Material Web, not tokens-only

Considered and rejected: hand-writing MD3's color/type/elevation tokens as
vanilla CSS, keeping the buildless approach. Rejected because MD3's value
here is as much in its interaction behavior (ripple, state layers, the
form-field/menu/dialog components' built-in a11y) as in its visual tokens,
and reimplementing that by hand is exactly the kind of premature
reinvention this project's own conventions warn against. The tradeoff
accepted in exchange: a build step, and a real external dependency this
project did not previously have.

## What's added

- **Build tooling**: `package.json` + [Vite](https://vitejs.dev/) — chosen
  over a hand-rolled bundler because Material Web ships as ES modules and
  needs bundling/tree-shaking to avoid pulling every component into every
  page; chosen over Webpack for a smaller config surface at this project's
  size. `npm run build` outputs to `static/dist/`; `npm run dev` for local
  iteration with hot reload.
- **`@material/web`** as a direct dependency (MIT-licensed). Components are
  imported per-page (e.g. `import '@material/web/button/filled-button.js'`),
  not globally, so a page only ships the components it uses.
- **MD3 token theme**: one `theme.css` (generated via Material Web's
  theme-builder from a single seed color, matching the current brand color)
  replaces the hand-written `style.css` custom properties. Light/dark
  handled by MD3's built-in scheme switching, not a bespoke media-query set.

## Glass finish

The hand-built shell (`.card-panel`, `.topbar`) has always used a frosted-glass
treatment — `--glass`/`--glass-2`/`--glass-line`/`--blur` in `style.css`,
translucent surfaces over the botanical backdrop, kept high-opacity so
clinical text stays legible. MD3 components didn't participate: any popover
surface a component opens (currently just `md-menu`, backing
`md-outlined-select` on `contacts.html`/`users.html`) fell back to Material
Web's own flat, opaque `surface-container` color, which reads as a different
product against the glass panel it opens from.

`components.css` now points `md-menu`'s exposed container-color custom
property at the same `--glass` token everything else already uses:

```css
md-menu {
  --md-menu-container-color: var(--glass);
}
```

**Known gap, not silently dropped**: `--blur`'s `backdrop-filter` can't be
applied this way. Material Web's menu doesn't expose a `::part` for the
element the container color lands on (`.items`, inside closed shadow DOM),
so there's no outside hook to blur through. The popover is translucent and
tinted to match, but not optically blurred like `.card-panel`. Revisit if a
future Material Web release adds that `::part`, or if this is worth a
`::part`-less workaround (e.g. wrapping the trigger in a blurred backdrop
element) when more MD3 surface components (`md-dialog`, `md-elevated-card`,
`md-snackbar`) are migrated in and hit the same gap.

Buttons and outlined text fields are unaffected on purpose: filled buttons'
solid container color is the accent, not a glass surface, and outlined text
fields already have a transparent container by default — nothing to change.

## What's replaced, page by page

Every existing custom component maps to a Material Web equivalent: buttons,
text fields (including the v2.14 password-visibility toggle — MD3's
`md-outlined-text-field` has a trailing-icon slot built for exactly this,
replacing the hand-rolled `wirePasswordToggles()` DOM-walk in `shared.js`),
select/menu, dialog (replacing ad-hoc `<details>`-based disclosure where a
true modal is warranted), snackbar (replacing the existing toast pattern),
chips (plan/status pills), and the data-table-like list rows already used
for practitioner rosters, consultation lists, and directory cards.

**Not replaced**: the sidebar navigation shell and breadcrumb pattern
([v2 CHANGELOG v2.4-v2.7](../CHANGELOG.md)) — Material Web has no drawer
component that matches this project's collapse behavior
(1250px/900px breakpoints, [v1/06-frontend.md](../v1/06-frontend.md)) closely
enough to be worth the rework; it stays hand-built CSS, now themed with MD3
tokens for visual consistency with the components around it.

`.sidebar` is a floating panel, not flush against the viewport edge: a 1rem
margin on top/bottom/left, `border-radius: var(--r-lg)`, and `--shadow-lg`
so it reads as a card resting over the page rather than part of the frame.
Its fill is the same frosted-glass mechanism as `.card-panel` (translucent
+ `--blur`) but tinted red on a top-lighter/bottom-darker gradient instead
of white, using the same light-on-dark token re-point `.ph` (the blood-red
header band) already established — `--ink`/`--accent`/etc. flipped to
near-white/light-tint values scoped to `.sidebar`, so nothing outside it is
affected. The gradient runs high-opacity throughout (`.88`→`.94`), same
"frosted, not tinted" reasoning as `--glass` itself — a lower top alpha
(`.62`) was tried first and `blur(16px)` over the page's light background
washed that stop out to near-white instead of a lighter red; `--blur`
carries the glass feel here, not letting the backdrop's own color show
through. Two spots needed a manual override rather than the re-point alone
covering them (both documented inline in `style.css`): `.sidebar-link:hover`
used the light-surface `--panel-2`/`--ink` pairing, which would have
repeated the near-white-on-near-white bug `.btn`'s hover had before that
was fixed; and `.brand-link`/`.brand b` read `color: inherit` rather than
an explicit `var(--ink)`, so `.sidebar` itself now sets `color: var(--ink)`
for them to inherit correctly.

## Live agent toast {#live-agent-toast}

New this version. `consult.html`'s composer shows an `md-snackbar` (MD3's
persistent-until-dismissed variant, not the auto-hide default — this one
should stay up for the full request) the moment a question is sent,
fed by the [live progress stream](08-api.md#live-progress-stream):

- A line naming the currently-running role in plain language — "Librarian is
  choosing sources…", "Specialist is drafting an answer…", "Checker is
  verifying citations…" — not the internal function names, so a
  practitioner unfamiliar with the seven-role architecture still gets a
  clear status.
- A running token counter (`input + output`, updating as each `agent_done`
  event arrives) — cumulative across the request, not per-role, since the
  practitioner's question is "how much is this costing," not "how much did
  the Librarian specifically use."
- On the bounded retry ([07](07-ai-team.md)), the line changes to "Checker
  flagged part of the answer — Specialist is revising…" rather than looking
  like the same step repeating.
- Collapses to the existing verdict badge the moment the `result` event
  arrives — the toast is a during-request affordance, not a permanent UI
  element.

No new component needed beyond stock `md-snackbar`; the token counter and
role label are just its content, updated via the SSE line-parser in
`shared.js` ([08](08-api.md#live-progress-stream)).

## Migration approach

Page by page, not a big-bang rewrite — each of the 24 existing HTML pages
converts independently, verified against its own spec section before moving
to the next, so a mid-migration deploy always has a working (if visually
mixed) site rather than a long-lived broken branch. See
[TODO.md](TODO.md) for sequencing.

## Operational impact

See [11 · Operations](11-operations.md#build-step) — deployment now includes
a build step before the static assets are servable, which did not exist in
any prior version.
