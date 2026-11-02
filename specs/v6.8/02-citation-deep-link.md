# v6.8/02 — Citation deep-link

## What

On a generated answer, clicking a `[K1]`-style citation opens the
knowledge library in a new browser tab, at that exact document, scrolled
to the exact passage (or PDF page) the citation points to — folder
included, once `01` ships.

## Current behavior

`practitioner/consult/+page.svelte`'s `onAnswerClick` only scrolls the
*same* page down to that citation's entry in the Sources accordion:

```ts
function onAnswerClick(e: MouseEvent) {
    const btn = (e.target as HTMLElement).closest('.cite') as HTMLElement | null;
    if (!btn) return;
    document.getElementById(`source-${btn.dataset.cite}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
```

That's staying — it's a reasonable "where did this come from in the
answer" affordance on its own. This spec adds a *second*, explicit
action (a small open-in-library icon/button next to each citation,
inside the Sources accordion entry it already scrolls to) that opens
the real document.

## Why this needs a new route, not just a new button

Today, both viewers that could show "the document, at this location"
are dialogs opened from client-side state on a list page — the admin
Library page's `viewDoc`, and `practitioner/knowledge/+page.svelte`'s
mirror of it (`v6.7/03`). Neither has a URL of its own: there's nothing
to `window.open()`. Making the citation open "in a new tab" requires an
actual routed page.

New route: `practitioner/knowledge/[id]/+page.svelte` — the same
viewer UI the existing dialog already has (extracted text, or the
original PDF inline — `v6.7/03`'s exact `Dialog`/iframe/pre-wrap-text
pattern), just as its own page instead of a dialog over the list.
`practitioner/knowledge/+page.svelte`'s existing "view" action links
here instead of opening its dialog in place — same component, reused,
not duplicated.

The admin Library page gets the equivalent `admin/[id]/+page.svelte`,
for the same reason and the same reuse — and because `01`'s folder
breadcrumb needs somewhere to link *back* to the folder's filtered list
view, which only makes sense from a real page.

No new backend route for content: `GET /api/sources/{id}`, `/text`, and
`/original` already exist and already carry the right auth
(`auth.require_admin_or_pro_practitioner` — the same gate `v6.7/02`
tightened the dialog viewer to) for exactly this. `01`'s `folder_path`
rides on the same existing payload.

## Carrying the location

Every cited source in a consult result already carries a `locator`
(`"page 3"`, `"pages 3–4"`, `"passage 2 of 5"` — `app/main.py`'s
`_locator()`) and a `kind` (`"chunk"` or `"entity"`). The new
open-in-library button:

- Only appears for `kind: "chunk"` — an `"entity"` source (a concept
  node the traversal pulled in, not a passage of a specific document)
  has no single document or page to point at. Clicking a `[K]` marker
  for an entity-kind source keeps today's scroll-to-accordion behavior
  only; no new button renders next to it.
- Needs the source's `document_id`, not just its chunk `id`
  (`f"{document_id}:{chunk_index}"` today) — exposed explicitly as its
  own field on each `sources[]` entry in `app/main.py`'s consult result,
  rather than the frontend parsing an internal id format.
- Opens `practitioner/knowledge/{document_id}?locator={encoded
  locator}` in a new tab (`window.open(url, '_blank')`).

## Scrolling to the location once the tab opens

- **PDF-backed source**: `<iframe src="{originalUrl}#page=3">` — the
  `#page=N` fragment is honored by every major browser's built-in PDF
  viewer (Chrome, Firefox, Safari, Edge), so no PDF.js integration or
  new dependency is needed. `locator`'s `"pages 3–4"` form opens at the
  first page of the range.
- **Text-backed source**: the viewer already has the full extracted
  text and the chunk's own text (already returned as each `sources[]`
  entry's `snippet` in the consult result, and available again from
  `GET /api/sources/{id}/text` on the detail page). `locator`'s
  `"passage N of M"` form is resolved by chunk index, not by searching
  for the snippet as a substring (a short/common passage could match
  more than one place) — the detail page finds the chunk at that index
  the same way `store.chunk_pages`/`_link_chunks_in_order` already
  order chunks, scrolls it into view, and highlights it (same visual
  treatment a found-text search highlight gets, nothing new to design).

## What this does not do

- No in-viewer "next/previous citation" navigation — one citation, one
  open, one location; stacking multiple open tabs from one answer is an
  accepted, ordinary outcome, not a UX gap to solve here.
- No change to how citations are matched or rendered inside the answer
  text itself (`$lib/markdown.ts`'s `renderAnswerHtml`, and the
  grouped-bracket (`[K1, K3]`) parsing `v6.4` already fixed) — this adds
  a second action available from the existing Sources-accordion entry,
  not a new citation syntax.
