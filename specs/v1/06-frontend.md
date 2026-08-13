# 06 · Front end

Three files, no framework, no build step: `static/index.html`, `static/app.js`,
`static/style.css`. Served by FastAPI, cached `no-store`.

## Information architecture

Two portals behind a segmented switch. Each is a **numbered sequence**, because the
first version showed three columns of equal-weight panels and gave no clue where to
start.

```
Practitioner                          Knowledge admin
┌──────────┬──────────┬────────────┐  ┌──────────┬────────────┬──────────┐
│ ① Patients│ ② Patient│ ③ Ask      │  │ ① Teach  │ ② The      │ ③ What   │
│           │   file   │   Clinic   │  │   Clinic │   library  │   Clinic │
│  search   │  record  │  toolbar   │  │ dropzone │  search    │   knows  │
│  filter   │  entries │  thread    │  │ preview  │  filters   │  coverage│
│  list     │  add     │  composer  │  │ paste    │  cards     │  graph   │
│  add      │ ② Past   │            │  │ kind     │  pagination│  audit   │
│           │  consults│            │  │ origin   │            │          │
└──────────┴──────────┴────────────┘  └──────────┴────────────┴──────────┘
```

Collapses to two columns under 1250 px and one under 900 px.

## Practitioner flow

1. **Choose a patient** — search by name, filter by country, list with initials
   avatars and entry/consultation counts. Erase is an icon revealed on hover, and
   takes two clicks (the icon becomes a tick).
2. **Read the file** — patient header, then record entries with a glyph per kind
   (flask for a lab, clock for history, pencil for a note, speech bubble for a saved
   summary). A long entry clamps to ~5 lines with a fade and expands on click, so one
   saved summary cannot push the rest of the record off screen.
3. **Ask** — a compact toolbar (grade threshold with a live pill, verification
   toggle, both with `?` explanations), the thread, then a chat composer. Enter
   sends, Shift+Enter newlines.

**Past consultations** lists saved sessions; opening one replays its turns with
citations, verdicts and traversal intact, and asking again continues that thread.

### An answer, rendered

- The question as a bubble.
- The verification badge — shield/`verified against its sources` or
  triangle/`needs review` — with the Checker's note and any unsupported claims.
- The answer, with `[S1]` markers that scroll to and expand their source on click.
  Light markdown (`**bold**`, `*italic*`) is rendered **after escaping**, so it
  cannot inject markup.
- **Sources behind this answer** — label, title, grade pill coloured by band,
  locator ("page 4"), and a `via` tag when the passage was not directly opened:
  `on point`, `continues`, `linked`, each explaining itself and listing the shared
  concepts. A `linked` source is marked with an amber left border.
- **How Clinic chose** — the Librarian's reasoning, what it opened, the traversal
  breakdown, the concepts looked for, and any truncation.

**No match** renders as a bordered notice, not as an answer dressed up in the same
styling — the assistant was never asked to write one.

## Admin flow

1. **Teach** — a dropzone (drag, click, or keyboard) with a real preview: PDFs
   render their first page in an `<object>`, text files show a snippet. Or paste
   text. Kind and origin each carry a `?`.
   A duplicate returns inline with a one-click **Replace it with this upload**, the
   upload still in the form.
2. **Curate** — full-text search, four filters and a clear button on one row, source
   cards, pagination at 5 per page. Each card: kind glyph, title, grade pill,
   provenance line, size and ingest date, summary, topics, a grade slider whose
   plain-language meaning updates as you drag, metadata and remove icons, and
   *Read it in full* inline. Remove asks for confirmation, naming the source and its
   passage count.
   The reader overlay leads with metadata, then — when an original file was kept —
   **Open the original file**, saying plainly that tables, figures and layout survive
   there where the extracted text lost them. Sources with no original (pasted text,
   or ingested before the file store existed) simply do not show the link.
3. **Check** — coverage by topic with proportional bars; **How it is connected**
   (concepts, passage links, reading-order edges, connected source pairs) with
   *Link N unlinked sources* and *Tidy the index*; the audit trail, five rows tall
   with the rest scrolling, each row tagged `library` or `patient vault`.

## Design system

`style.css` is token-first: colours, radii, shadows, blur and easing at the top, so
the product can be retuned from one place.

**Glassmorphism.** Panels are `rgba(255,255,255,.72)` with `backdrop-filter:
saturate(1.15) blur(16px)`, a light hairline along the top edge for glass thickness,
and a translucent sticky topbar. Deliberately high opacity: frosted, not tinted, so
clinical text stays fully legible.

**Panel headers** are a solid blood-red band (`#6a0814`), rounded to meet the panel's
top corners. `.ph` re-points the ink, muted and accent tokens for its descendants, so
the title, icon, count and help button read light-on-dark; the panel body below keeps
the frosted white surface and the warm clinical palette.

**Backdrop.** Two fixed layers behind everything: three slow-drifting radial washes
(so the blur has something to blur) and a pale repeating botanical vector as an
SVG data-URI.

**Botanical layer** — vectors and CSS only, no icon glyphs:
- a drawn sprig beside the wordmark, swaying on a 7-second loop
- a leaf watermark on empty panels, breathing between 7% and 12% opacity
- leaves made purely from `border-radius: 0 100% 0 100%` rotated 45°
- a `.vine` divider: two gradient hairlines either side of a leaf

**Icons** are inline SVG — no font, no CDN, CSP-safe. Wordy controls became icon
buttons; every one carries `data-tip` and an `aria-label`, so an icon-only control is
never a guess. Tooltips are generic (`[data-tip]`) and appear on hover **and**
keyboard focus.

**Motion** — entrances explain where a thing came from; the rest is input feedback.
Staggered panel lift-in, row slide-in, turn lift-in, toast pop, overlay scale-in,
press translate, focus ring. All of it collapses to ~0 ms under
`prefers-reduced-motion`.

**Feedback** — toasts bottom-right for every action; shimmer skeletons while loading;
empty states that name the next action rather than dead-ending.

## Accessibility

Semantic landmarks, `role="tablist"` on the switch, labels or `aria-label` on every
control, `:focus-visible` rings, keyboard-operable patient and session rows and
dropzone, `aria-live` on the toast region, and tooltips reachable by focus.

## Bugs this UI has already produced

Recorded because they are the kind only a rendered screenshot catches:

1. **`.reader-wrap { display: flex }` overrode the HTML `hidden` attribute**, leaving
   an invisible full-page overlay that swallowed every click. Fixed with
   `display: none` plus `:not([hidden])`. It reached production briefly.
2. **Stale Cloudflare assets.** `/api/sources` changed from an array to an object;
   the cached `app.js` called `.length` on it, got `undefined`, and rendered "the
   library is empty". Fixed with `Cache-Control: no-store` on `/static/` and a `?v=`
   cache buster that is **bumped on every deploy**.
3. **Icon swap broke click handlers** — the event target became the inner `<svg>`.
   All handlers now use `closest('[data-…]')`.
4. Inline padding on a citation chip pushed trailing punctuation away
   (`isolation [S1] .`).
5. `.nm`/`.sub2` were inline, so a name ran into its metadata (`Anna K.SK · 3 entries`).
