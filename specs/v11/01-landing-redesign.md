# v11/01 — Landing page + public nav redesign

## Brief

Direct instruction: redesign the landing page(s). Copywriting should
be about professional practitioners who, with the help of AI tuned
only to a knowledge base, can help more — client-facing copy comes
first, practitioner-facing copy second. Add more than one SVG
illustration to the landing page. Redesign the navbar. The logo must
never sit in a background box (it did, in the navbar, in a red one).

## What changed

### Copy — client-first, then practitioners

The previous landing page's hero headline ("An AI assistant
practitioners can put their name behind") and its four-pillar trust
section were both written in the practitioner's voice — explaining the
pipeline's mechanics as something a practitioner should feel good
about, not something a client should feel reassured by. Rewritten so
every section before the practitioner-facing one speaks to a
prospective client:

- **Hero** — "Practitioners who can help *more* — with an AI that only
  knows your library," subcopy: "No open-internet guesses. Every
  practitioner here works with an AI assistant tuned only to their own
  vetted knowledge base — so they spend less time searching, and more
  time on you." Carries the brief's exact value proposition
  (professional + AI-tuned-to-knowledge-base = can help more) as
  client-facing marketing copy, not an internal mechanics explainer.
- **Lede row** (generic AI vs. this one) — reworded from "you" (the
  practitioner) to "your practitioner."
- **Trust pillars** (grounded / cited / checked / graded) — reworded
  from instructions ("you set the bar") to reassurance ("your
  practitioner sets the bar") — same four claims, client voice.
- **Practitioners taking new clients strip** — unchanged, already
  client-facing (browsing real practitioner profiles).
- **New "For practitioners" section** — added near the end, after
  every client-facing section above it. This is where the brief's
  "help more clients" framing is stated directly to practitioners
  ("Help more clients, without cutting corners"), absorbs the old
  "every role on the team..." trust quote as supporting proof inside
  this section instead of its own standalone block, and carries the
  "Apply as a practitioner" CTA.
- **Closing CTA band** — unchanged structurally (both audiences,
  side by side), copy untouched.

### New SVG illustrations (3, not stock icons)

Added as their own reusable components in `web/src/lib/components/art/`,
drawn in the same stroke-and-soft-fill language `Icon.svelte`/
`Sprig.svelte` already use (so they read as the same brand, just at
illustration scale instead of a 24x24 glyph) rather than a generic
stock "AI robot" or "chat bubble" cliché:

- **`NetworkArt.svelte`** — a document node linked to smaller outlying
  nodes, standing in for "your own curated, connected library." Placed
  beside the hero copy, replacing empty space that column previously
  had none of.
- **`GroundedArt.svelte`** — an open book with a verification
  checkmark badge overlapping its spine. Placed beside the trust-
  pillars list.
- **`PractitionerArt.svelte`** — a practitioner silhouette paired with
  a small AI-assistant chat bubble carrying a spark glyph, connected by
  a dashed line. Placed beside the new "For practitioners" section.

### Navbar redesign

- **The logo is never boxed again.** `PublicNav.svelte`'s `.mark` used
  to be a 2rem square with `background: linear-gradient(135deg,
  var(--rail-top), var(--rail-bottom))` behind the bare `Sprig` SVG —
  the "red box" called out directly. It's now just the SVG, tinted
  `var(--accent-ink)` via `currentColor`, same as everywhere else the
  mark appears (Rail, the footer) — no background, no box, anywhere.
- Nav links gained a left-to-right underline wipe on hover/active
  instead of a plain color change — the only other visual change to
  the bar itself; height, spacing, and link order are unchanged.
- The CTA button is relabeled from "Get started" to **"Sign up as a
  client"** (desktop and mobile). Found live, same session: a client's
  own path through the site was real (`/signup` already creates a
  client account, tied to a chosen practitioner) but nothing on the
  landing pages named it — a generic "Get started" button next to a
  "For practitioners" link reads ambiguous about which role it's for.
  This is a labeling fix, not a new flow.

## What this doesn't touch

- No backend changes — this is a frontend/copy-only spec.
- `/practitioners`, `/signup`, `/login`, `/pricing`, `/faq`,
  `/contact`, `/privacy`, `/terms`, `/cookies` pages themselves are
  unchanged; only the shared `PublicNav` and the root landing page
  (`web/src/routes/(public)/+page.svelte`) were touched.
- The hero/CTA-band red gradient background is unchanged — kept per
  the standing direct instruction from earlier this session, not
  revisited here.
