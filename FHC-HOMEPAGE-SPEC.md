# Functional Health Collaborative — Homepage Rebuild Spec

Source documents: `~/Downloads/refhcwebupdate/FHC-website-handoff/` (index.html + images + README) and `Functional Health Collaborative – Website Style Guide.pdf`, both dated 2026-11-11, by @Kreetta Ryödi. This spec translates them into a concrete change plan against the current SvelteKit app.

## 0. Strategic reframe (confirmed with user: full pivot)

The current `(public)` route group implements a **multi-practitioner marketplace**: a directory (`/practitioners`), per-practitioner profiles fetched from an API (`/coach/[id]`), client self-signup (`/signup`), a practitioner-onboarding flow (`/join`), and authenticated accounts (`/login`, `/account`) — all in a green "nature/botanical" theme under the name "Functional Health Collab."

The handoff describes a different business: **a single telehealth practice**, "Functional Health Collaborative," with three named practitioners, fixed programs/pricing, no client self-signup, and no marketplace directory. Brand is navy (`#00004C`) / burgundy (`#7A1F3D`) / copper (`#D79351`).

Decision: **pivot fully**. This spec covers the homepage rebuild in detail (fully specified by source docs) and names the marketplace routes/features that become orphaned by the pivot, for a follow-up decision — removing them is a separate, larger change (touches API usage, auth, `/join`, `/account`) and isn't specified by these two documents, so it's out of scope here pending explicit sign-off per route.

## 1. Design tokens

Replace the nature palette in `web/src/routes/(public)/+layout.svelte` (`:global(:root)` block, lines 16–30) with:

| Token | Hex | Used for |
|---|---|---|
| `--pub-navy` | `#00004C` | headings, logo, menu text, footer bg |
| `--pub-burgundy` | `#7A1F3D` | section labels, links, ticks, feature panels |
| `--pub-copper` | `#D79351` | primary buttons (navy text), highlight numbers, header photo border |
| `--pub-warm-grey` | `#E6E4DD` | alternating section bg, card borders |
| `--pub-header-bg` | `#D8D0C5` | hero section background |
| `--pub-bg` | `#F4F2ED` | main page background |
| `--pub-text` | `#1C1C33` | body text |
| `--pub-text-muted` | `#4A4A5E` | secondary text |
| `--pub-card-bg` | `#FFFFFF` | cards |

Fonts: add Google Fonts link for `Bricolage Grotesque:wght@500;600;700` + `Figtree:wght@400;500;600` (handoff `index.html` lines 7–8) to `web/src/app.html` or `Seo.svelte`. Headings use Bricolage Grotesque 600; body/buttons/menu use Figtree.

| Element | Font | Size | Weight |
|---|---|---|---|
| H1 | Bricolage Grotesque | clamp(36px,4.4vw,54px) | 600 |
| H2 | Bricolage Grotesque | clamp(30px,3.4vw,42px) | 600 |
| Card/program titles | Bricolage Grotesque | 19–26px | 600 |
| Body | Figtree | 17px / 1.6 | 400 |
| Buttons/menu | Figtree | 16–17px | 600 |
| Section labels | Figtree | 14px, uppercase, 0.12em tracking, burgundy | 600 |

Shapes: buttons fully pill, min-height 52px; primary = copper fill + navy text (not white — white-on-copper fails contrast per the guide); secondary = 1.5px navy outline. Card radius 20–24px; large panels/photos 28px. Header photo: 3px copper border, 28px radius, soft shadow. Team portraits: 4:5 ratio, 24px radius. Max content width 1160px (1280px for header), 32px side padding. Section vertical padding ~96px. Mobile: all grids collapse to one column.

## 2. Page structure (11 sections, replacing the current 7-section homepage)

Target file: `web/src/routes/(public)/+page.svelte`. All current content (`healthFocusAreas`, `pillars`, `steps`, practitioner-directory fetch, botanical SVG hero) is replaced — none of it maps to the new brief.

| # | Section | Anchor | Content source |
|---|---|---|---|
| 1 | Menu | — | handoff lines 19–33 — see §3 |
| 2 | Hero | `#top` | headline, subline, 2 buttons, `hero-group.jpg` |
| 3 | Our approach | `#approach` | 1 paragraph, static copy |
| 4 | What we solve for | — | burgundy panel, "100+" stat |
| 5 | Who we are | `#about` | 3 portraits + bios, testing-partner logos |
| 6 | Why women choose us | — | 8 cards, burgundy bg |
| 7 | How to work with us | `#how` | 8 numbered steps |
| 8 | Programs | `#programs` | 3 pricing cards + comparison note |
| 9 | What women say | — | 3 testimonials (**placeholder content — blocked, see §5**) |
| 10 | Ready to start? | `#book` | CTA panel |
| 11 | Footer | — | see §4 |

All copy is verbatim in the handoff `index.html` (read in full during research) — implement text content exactly as written there; don't paraphrase.

## 3. `PublicNav.svelte` changes

- Brand: replace `Sprig` icon + "Functional Health Collab" wordmark with the two-circle logo mark (`index.html` line 22, inline SVG, navy + copper strokes) and two-line lockup: "Functional Health Collaborative" (bold) / "Personalised Perimenopause and Menopause Care" (burgundy, small).
- Links become in-page anchors, not routes: `#approach` Our approach, `#how` How it works, `#programs` Programs, `#about` About us (About us anchors to "Who we are" until the standalone About page exists — handoff README confirms this is planned, not yet built).
- Drop: Dashboard/session-aware login state, "Sign up as a client", "Log in" — this marketing site has one CTA only.
- CTA: pill button, copper fill / navy text, "Book a free intro call" → scrolls to `#book` until a real booking link is supplied (see §5).

## 4. `PublicFooter.svelte` changes

- Background navy (`--pub-navy`), text white / `#CFCFE3` muted.
- Brand block: "Functional Health Collaborative" + tagline, no Sprig icon (or keep mark in white/copper if a monochrome variant is cut).
- Link group: Our approach, How it works, Programs, About us (anchors, not the Legal group that exists today) + `mailto:` email (blocked, see §5).
- Keep: disclaimer line — handoff explicitly asks to preserve "works alongside, not in place of, GPs and medical specialists" (README note, PDF page 4). Reuse `/privacy` and `/terms` routes already in the app for the "[Privacy policy] · [Terms]" links.
- Copyright: "© 2026 Functional Health Collaborative".

## 5. Blocked / still-to-be-supplied (don't fabricate these)

Per the handoff README §"Still to be supplied" — implement with explicit TODO placeholders, not invented data:
- Booking link for the 15-min intro call (all "Book" buttons/anchors currently point at `#book` which scrolls to the CTA section, not an external scheduler)
- Contact email (footer `mailto:`)
- 3 client testimonials (quote + first name + age/country) — ship the section with the literal bracketed placeholder text from the handoff, don't invent testimonials
- "Meet the team" link target (future `/about` page with full team profiles — not this phase)

## 6. Assets

Copy from `FHC-website-handoff/images/` into `web/static/images/fhc/`:
- `hero-group.jpg`
- `portrait-alex-ginsburg.jpg`, `portrait-jana.jpg`, `portrait-kreetta-ryodi.jpg`
- `logo-nordic-laboratories.png`, `logo-mira.{png,svg}`, `logo-precision-analytical-dutch.{png,svg}` — prefer SVG where present per the handoff note ("SVGs are the originals where available")

Update `Seo.svelte` / `og:site_name` / org JSON-LD `name` from "Functional Health Collab" to "Functional Health Collaborative", and page title/description to match the new tagline and positioning (hormone/metabolic/gut care for perimenopause & menopause — not the current "practitioner directory" framing).

## 7. i18n note (don't build yet, just don't block it)

Handoff README: site must eventually support English, Dutch, Slovak, French, German, Italian, Finnish. No i18n library exists in this codebase today. Out of scope for this pass — flagged so copy isn't hardcoded somewhere that would be awkward to extract later (e.g., prefer component props/constants for strings over inline template text where cheap to do).

## 8. Explicitly out of scope here (needs separate sign-off)

These are consequences of the pivot but aren't specified by the two source docs, so implementing them isn't covered by this spec:
- Removing/redirecting `/practitioners`, `/coach/[id]`, `/signup`, `/join`, `/account`, `/login` and their backend usage
- Any change to the API/auth/practitioner-platform backend (`PLAN.md`'s clinic platform) — the marketing site and the clinical platform may legitimately stay separate (practice website vs. internal tool)
- The future `/about` page with full team profiles (explicitly "later" per the handoff)

## Success criteria

- `/` renders the 11 sections above, in order, matching the handoff's copy, colors, type and spacing (desktop ≥1160px and mobile <640px both checked)
- Nav/footer use the new brand name, anchors, and palette; no leftover green/nature tokens or marketplace CTAs on the homepage
- No fabricated booking link, email, or testimonials — placeholders are visibly marked TODO in code (comment) and, where user-facing, use the bracketed placeholder text from the handoff
- Disclaimer line preserved in the footer
