# Three consult page bugs, found and fixed live

## 1. "How it searched" dumping the whole conversation as the seed query

`general_lookup` mode's `search_query_repr` was set from the internal
`question` variable — which has the entire multi-turn history block
prepended for the embedding call (`app/main.py`'s `history_block`
logic) — instead of `body.question`, the practitioner's actual typed
text. A real multi-turn session's "How it searched" summary showed the
full accumulated transcript instead of a short seed query. Fixed to
use `body.question` directly, matching how `deep_research` mode's
`seed_search.search_query` (the LLM-formed query) already displayed
correctly.

## 2. Auto-selecting the first client, and losing the selection on refresh

Two related issues: `onMount` fell back to `data.clients[0]?.id` when
no client was named in the URL — landing on the page silently opened
whichever client happened to sort first, an implicit selection of
clinical data the practitioner never actually made. Separately,
refreshing mid-conversation reverted to that same default instead of
staying on the open conversation, since the URL never reflected
`clientId`/`sessionId` as they changed.

Fixed: `onMount` no longer has the `data.clients[0]` fallback — only a
real deep link (a URL that already names a client) restores a
selection; otherwise the page shows an explicit "Pick a client to
continue" prompt. A new `$effect` keeps `?client=`/`&session=` in the
URL in sync via SvelteKit's `replaceState`, so a refresh or a
copy-pasted link now lands back on the same conversation.

## 3. The sidebar going completely unclickable — a regression from fixing #2

Found live, same day #2 shipped: the consult page's entire sidebar
rendered correctly — client names visible, styled, everything looked
normal — but nothing was clickable, always on the first arrival at the
page in a session, never after navigating away and back within the
app. A hard refresh did not fix it (ruling out stale cache as the
cause).

Root cause: the new URL-sync `$effect` called `replaceState` during
the render, sometimes while SvelteKit's router was still mid-
transition into the page. `replaceState` can throw in that exact
window; an uncaught error inside a `$effect` breaks reactivity for the
*rest of the component*, not just that one effect — which presents as
"nothing responds to clicks," with no visible error anywhere in the
UI. This only happened on a genuinely fresh arrival (router mid-
transition) and never on an in-app remount (router already idle),
which is exactly the reported reproduction pattern.

Fixed: wrapped the `replaceState` call in `try/catch` — URL sync is a
nicety and must never be able to take the rest of the page down with
it — and switched from passing a bare relative string to building a
proper absolute URL via `new URL(page.url)`, which is the more correct
way to call `replaceState` regardless of this specific failure mode.

## Two smaller composer changes, same batch

Cmd/Ctrl+Enter now submits the question (plain Enter still inserts a
newline, matching every other chat UI's convention). The live progress
indicator shows only the current step, not a growing list of every
finished one stacked underneath it — a completed step is replaced by
whichever one runs next.

## What this does not change

None of these touch the retrieval pipeline or Reasoner logic — all
four are consult-page presentation/state-management fixes. `v6.4`'s
chat redesign and hallucination fix are otherwise unchanged.
