# 03 · Visual redesign: composition, hierarchy, density

Companion to [01](01-sveltekit-frontend.md), not a restatement of it. 01 is
the *how* — how the current look moves into SvelteKit, what component
library replaces Material Web, how tokens travel. This document is the
*what* — what each screen should actually look like once it's rebuilt.
01's own "What doesn't change" section currently asserts the visual
identity is *"kept literally, not reinterpreted"* and lists *"a visual
redesign"* under Explicit non-goals; both statements are revised by this
document — see [§Updates to 01](#updates-to-01) at the bottom. The
identity (colors, gradient, glass, botanical motifs) is still kept
literally. The *composition* — what's built out of that identity, on which
screens, at what visual weight — is not; that's what was still missing,
per the request that produced this doc: *"aside from the technical, the
visuals..."*

**Status: spec only.** No code, no HTML mockups, no changes to `static/`,
`src/`, or `app/`. Same constraints as every doc in this folder.

---

## The tension, named directly

"Keep the gradient identity, user loves it" and "less cramped" pull in
different directions the moment you look at how the identity is actually
*applied* today, not just what it looks like in isolation. Grepping
`static/*.html` and `static/*/*.html` for `.card-panel` and `.ph.botanic`
confirms it: **every single content panel in the app, on every page, gets
the identical treatment** — frosted glass (`--glass`/`--blur`), a
`box-shadow: var(--shadow)`, and (on the large majority) a full red
gradient `.ph.botanic` header band. `static/practitioner/dashboard.html`
alone stacks five of them (welcome panel, checklist, stat cards' own
implicit panel styling, recent-contacts, history) in one scroll.
`static/index.html`'s admin dashboard puts three side by side, each with
its own red band, each visually shouting at the same volume.

**That uniformity *is* a real, separate contributor to "cramped" — not
because glass/gradient is inherently heavy, but because when everything
gets the loudest treatment the app has, nothing reads as more important
than anything else, so a screen with five panels reads as five
equally-loud rooms instead of one main event with supporting detail.**
The fix isn't diluting the identity to make room — the existing
`.leafmark` watermark technique, already used exactly twice
(`practitioner/consult.html`'s `#ask-panel`,
`public/coach.html`'s `#signup-panel`, both from prior
[v3/17](../v3/17-full-app-redesign.md) fixes), is proof the app already
knows how to make one panel read as "this is the one that matters." The
fix is applying that same discipline everywhere: **reserve the full
red-gradient-header treatment for the one panel per screen that's actually
the reason a person opened it, and give everything else a quieter surface**
— which simultaneously fixes the "everything is shouting" density problem
and makes the gradient identity itself read as *emphasis* again instead of
wallpaper. Both goals, one mechanism — the tension resolves rather than
trades off.

---

## Surface weight: a two-tier system, replacing "every panel is a `.card-panel`"

Concretely, two tiers instead of one:

**Tier 1 — `.card-panel` (unchanged CSS, narrowed usage).** The full
treatment: glass, blur, shadow, and — when it has a header — the red
`.ph.botanic` gradient band. Reserved for: the single primary panel on a
screen (the thing the screen exists for), and marketing/first-run moments
where a stronger visual pull is the point (`coach.html`'s signup panel,
the public directory's hero — see below). At most one `.ph.botanic` red
band visible per screen without scrolling, as a rule, not a suggestion —
this is the actual enforceable version of "less cramped."

**Tier 2 — `.panel` (new class, proposed values below).** A quieter
surface for everything that's supporting content, not the main event: a
flat or barely-tinted background, a hairline border instead of glass+blur,
no drop shadow, and — critically — **no red header band**; a plain-text
or muted-icon label instead. Same border-radius (`var(--r-lg)`) and
padding scale (see [§Spacing](#spacing-applying-01s-scale-instead-of-just-proposing-it)
below) so it still belongs to the same visual family, just recessed.

```css
/* Proposed, alongside .card-panel in the same file/module */
.panel {
  background: var(--panel-2);   /* existing token, #fbfaf8 — already used
                                    for hover states, never yet for a
                                    panel's own resting surface */
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  /* no backdrop-filter, no box-shadow, no liftIn — a supporting surface
     doesn't need an entrance to announce itself */
}
.panel > .ph {
  /* quiet header: reuses .ph's layout (flex, padding, border-bottom)
     but not its background — plain text on the panel's own surface */
  background: none; color: var(--ink-2); border-bottom: 1px solid var(--line);
}
```

This is a **rebalancing of an existing system, not a new one** — `--glass`,
`--panel-2`, `--line`, `--ph`'s layout rules all exist today and are
reused as-is; `.panel` is a second combination of tokens the app already
has, not a new visual language to learn or maintain.

---

## Spacing: applying 01's scale instead of just proposing it

[01 §Spacing/type scale](01-sveltekit-frontend.md#spacingtype-scale-made-explicit-instead-of-ad-hoc)
defines `--space-1` through `--space-6` and a type scale but doesn't apply
them to anything — it's a token list, not a decision. Applied here,
concretely, to the specific values that currently vary by convention
rather than system:

| Context | Today (ad hoc) | Redesigned |
|---|---|---|
| `.pb` (card body padding) | `1rem` | `--space-4` (1rem — unchanged, already right) |
| `.pb.tight` (used on lists/tables) | `.6rem` | `--space-3` (.75rem — today's value undershoots the 8px-minimum-touch-adjacent-padding norm this app otherwise follows; bump it) |
| `.data-table td` | `.55rem .6rem` | `--space-3` vertical, `--space-3` horizontal — today's asymmetry (.55 vs .6, an artifact of two separate hand-typed numbers) becomes one deliberate value |
| Dialog content gap (`admin/users.html`'s `#np-dialog`, `practitioner/clients.html`'s `#cl-dialog`, both `style="display:grid;gap:.4rem"` typed per-instance) | `.4rem` | `--space-3` (.75rem) as the `Dialog` component's own default, not a value every call site retypes |
| Panel-to-panel vertical rhythm (`.card-panel + .card-panel { margin-top: 1rem }`) | `1rem` flat | `--space-5` (1.5rem) between **Tier 1 and Tier 2** panels specifically — a visible gap between "the main thing" and "supporting detail" reinforces the hierarchy the two-tier system establishes; `--space-4` between two Tier 2 panels (they're peers, don't need as much separation) |

The pattern across every row: today's values are *close* to a coherent
scale already (this app's instincts were good), they just don't share a
single source, so small inconsistencies (`.55rem` vs `.6rem` vs `.4rem`
all meaning roughly "a bit of breathing room") compound into a feeling of
randomness across dozens of files. One scale, applied, removes that
without changing the overall footprint by much — this is not a "make
everything bigger" pass, it's a "make everything *consistent*" pass, which
is most of what "less cramped" actually means once the honest MD3-collision
cases ([v3/15 §Field density](../v3/15-design-system.md#field-density))
are separately fixed by dropping MD3 (per [01](01-sveltekit-frontend.md)).

---

## Per-portal redesigns

### Public / marketing

**`directory.html` (site root per [01](01-sveltekit-frontend.md#one-deliberate-ia-change)) is the biggest composition change in the app.**
Today it's `<main class="pane on centered" style="max-width:72rem"><section class="card-panel">` — the entire browse/discovery surface, hero copy,
search, filters, and the practitioner grid, is one Tier-1 card boxed at
72rem, exactly the template built for a settings panel or a single-record
detail view, applied to what
[v3/17 PUB5](../v3/17-full-app-redesign.md#pub5--low-the-directory-and-about-page-have-no-visual-identity-beyond-the-card-grid)
already correctly called *"the product whose entire public-facing job is
to get a visitor to pick a practitioner."* A discovery surface shouldn't
live inside a bordered box at all.

**Redesigned:** the hero (today's `<p class="hint">` intro line, added by
[v3/17 PUB5](../v3/17-full-app-redesign.md#pub5--low-the-directory-and-about-page-have-no-visual-identity-beyond-the-card-grid))
becomes a real page-level band — full-width (within the `.app-main`
column), no card border, sitting directly on the botanical backdrop the
way the sidebar and topbar already do, with the search/filter row
underneath it. The practitioner grid (`#coach-grid`) comes out of the card
entirely and becomes the page's main content, each `.src` card kept as its
own Tier-1-*adjacent* surface (photos and practitioner info deserve their
existing card treatment — `.src`'s hover lift already works well per
[v3/17](../v3/17-full-app-redesign.md)) but no longer nested inside a
second, redundant card boundary. Net effect: one fewer layer of visual
containment on the single most important public page, more room for the
grid to breathe without changing `--space` values at all — the box itself
was the cramping.

**`coach.html`**: already the best-composed page in the app after
[v3/17 PUB2](../v3/17-full-app-redesign.md#pub2--medium-coachhtml-stacks-two-same-weight-ctas-with-no-framing-for-which-to-use)'s
fix — signup promoted to Tier 1 + leafmark, contact form demoted. This
document's only addition: the profile panel above them (`#coach-panel`,
today a plain `.ph.botanic` "PRACTITIONER PROFILE" band) is itself the
actual reason someone's on the page — demote *it* to Tier 2 (quiet header,
no red band; a visitor doesn't need "PRACTITIONER PROFILE" shouted at
them, they need to read the bio) so the signup panel's leafmark treatment
is the only red moment on the page, sharpening the hierarchy
[v3/17](../v3/17-full-app-redesign.md) already started.

**`login.html`/signup flows**: single-card, single-purpose pages — the
current one-`.card-panel`-in-a-centered-column template is already correct
for this kind of screen (one task, one focus, a box *should* contain it).
No composition change; these are the cases Tier 1 was designed for.

### Client portal

**`client/dashboard.html`**: three `statCard()` links (Questionnaire,
Files, Wearables) rendered as identical-weight `.card-panel`-styled
buttons in a `repeat(auto-fit, minmax(16rem,1fr))` grid — appropriate for
a page with no real primary/secondary distinction (a new client genuinely
needs all three with equal urgency). No Tier-2 demotion here; this is one
of the few screens where uniform weight is the *correct* call, worth
stating explicitly so the two-tier system isn't applied mechanically
where it doesn't fit.

**`client/questionnaire.html`**: single form, single card — same case as
login/signup, no change.

### Practitioner portal

**`practitioner/dashboard.html` is the densest page in the app and the
clearest case for the two-tier system.** Today: welcome panel (Tier 1
implicitly, no header), checklist (Tier 1, red header), stat-cards
(Tier-1-styled link cards), recent-contacts (Tier 1, red header),
history-panel (Tier 1, red header) — five to six full-weight surfaces in
one scroll, exactly the "everything shouting" problem named at the top of
this document.

**Redesigned, by actual priority** (a practitioner opens this page to
answer "what do I need to do today," not to admire five equal panels):

1. **Welcome panel stays Tier 1** but consolidated with the checklist —
   today they're two separate cards stacked with `margin-top:1rem`; a
   first-run practitioner's welcome *is* "here's what to do next," so
   merging them into one panel (name/plan/status chips at the top, the
   checklist rows directly below, no card boundary between them) removes
   a whole redundant panel boundary. Once the checklist is done (all three
   steps checked, per [v3/17 X4](../v3/17-full-app-redesign.md#x4--medium-onboarding-is-individually-good-empty-states-with-no-cross-page-checklist)'s
   existing hide-when-complete behavior), the welcome panel collapses back
   to just the name/status line — smaller by default once onboarding is
   done, not permanently larger to accommodate a state most sessions won't
   be in.
2. **Stat cards move to Tier 2** — three of these link-cards
   (`statCard()`) are a navigation aid, not the content; the red-header
   treatment was never applied to them directly (they don't have a `.ph`),
   but visually they compete at the same weight as the panels around them
   because of the shared `.card-panel` glass/shadow. Flattening them to
   `.panel`-tier removes one more "am I supposed to look here first"
   signal for the eye to sort through.
3. **History-panel (the practitioner's actual work list — past and
   current consultations) is the one that should read as Tier 1** — it's
   the highest-frequency, highest-value content on the page for a
   returning practitioner, currently given the same weight as
   "recent contact submissions" (a lower-frequency, admin-adjacent list).
   Swap their relative weight: history gets the full red-header treatment,
   recent-contacts moves to Tier 2.

**`practitioner/clients.html`**: the datatable itself
([v3/17 X3](../v3/17-full-app-redesign.md#x3--component-need-most-data-lists-should-be-real-data-tables-not-stacked-card-rows))
is correctly dense — a work list of clients is exactly the case where
scannable rows beat spacious cards, no change there. The panel *around*
the table stays Tier 1 (it's the only content on the page), no change.

**`practitioner/consult.html`**: already correct — `#ask-panel`'s
leafmark is the one Tier-1-with-emphasis moment, `#client-list` and
`#overview-panel` are supporting content. This document's only change:
demote `#client-list` and `#overview-panel`'s sub-cards (`Client
overview`, sessions, documents) to Tier 2 explicitly, since today they're
plain `.card-panel`s (Tier 1 by the current one-tier system) that happen
to read as secondary only because `#ask-panel`'s leafmark outshines them —
correct by accident, not by declaration. Making it explicit means the
hierarchy holds even as more panels get added to this screen later.

### Admin portal

**`static/index.html` (the knowledge-library dashboard) has the same
three-equal-panels problem `coach.html` had before
[PUB2](../v3/17-full-app-redesign.md#pub2--medium-coachhtml-stacks-two-same-weight-ctas-with-no-framing-for-which-to-use)
fixed it, never diagnosed because it's a workflow screen, not a marketing
one** — but the underlying problem (three same-weight red-banded panels
side by side, no signal for which matters most) is identical. Ingest
(`Teach Clinic`), the library list (`The library`), and the audit/graph
rail (`What Clinic knows`) are given equal visual weight; usage frequency
isn't equal — an admin opens this page to work the library list far more
often than to ingest a new source or check the audit trail. Redesigned:
**the library list (step 2) stays Tier 1**; ingest and the audit rail
become Tier 2 — quieter, still fully functional, no longer competing for
attention with the actual work surface. `.step`'s numbered-sequence framing
(1/2/3) stays exactly as-is on all three regardless of tier — the numbers
communicate workflow order, which is a different job than visual weight,
and conflating them would lose real information.

**`admin/users.html`**: the tabs/datatable/dialog composition from
[v3/16](../v3/16-users-page-redesign.md) is sound — a datatable is
correctly dense for its purpose, same reasoning as the practitioner client
list. The one open question: should `.ph.botanic`'s red header still
apply to `#practitioners-panel`/`#admins-panel` on a screen an admin
revisits many times a day, or is that exactly the kind of high-frequency
work surface where Tier 2's quieter chrome serves better, saving the red
band's visual weight for genuinely rarer, more consequential moments
(bulk actions, destructive confirmations)? **Recommendation: Tier 2** —
apply the same "is this the reason someone opened the page, or the
mechanism for doing the work" test used everywhere else in this document.
A datatable of practitioners *is* the reason the page exists, which argues
Tier 1 — but the red band's job here (loudly announcing "you are inside a
notable panel") has no audience left to convince on a screen someone
visits dozens of times; familiarity dilutes signal value the same way
uniform application across the whole app does. Flagged as the one
genuinely close call in this document, not asserted as obvious.

---

## Motion: extending [v3/17 X5](../v3/17-full-app-redesign.md#x5--low-the-motion-system-is-well-built-but-only-fires-on-entrance) to the tier system

X5's count-up animation (already shipped on every dashboard's stat
numbers) and the broader `liftIn`/`slideL` entrance system stay exactly as
specced in [01](01-sveltekit-frontend.md#token-strategy-css-custom-properties-carried-forward-almost-unchanged) —
ported to Svelte transitions (`in:fly`/`in:fade` wrapping the same
`--ease` timing and durations, so the *feel* doesn't change even though
the mechanism does). One addition specific to the two-tier system: Tier 1
panels keep the existing `liftIn` (opacity+translateY) entrance; Tier 2
panels get a strictly quieter `fadeIn`-only entrance (no translate) — the
same "which one is the main event" signal the visual tiers establish,
carried into motion instead of just color/shadow.

---

## Updates to 01

Two changes to [01-sveltekit-frontend.md](01-sveltekit-frontend.md), made
alongside this document:

- **"What doesn't change" → "The visual identity"** bullet: still true for
  *tokens* (color, gradient values, motion keyframes, botanical assets),
  now cross-links here for what's not literal — composition and per-panel
  weight.
- **"Explicit non-goals" → "A visual redesign"** bullet: removed as a
  non-goal, since this document is exactly that; replaced with a note that
  the *token* layer (colors, the gradient formula, `--glass`/`--blur`
  values) is what stays literal, cross-linked to this document for what
  changes.
