# v6.19/01 — Local embedder OOM fix, menu reliability rewrite

Two production incidents, found and fixed live, 2026-11-04.

## 502 Bad Gateway on retry (OOM crash loop)

Reported directly: "Why does my 3 dots..." then "When retrying
ingestion, I get 502 bad gateway."

Confirmed on the VPS (`journalctl`, `dmesg`): `clinic.service` was
crash-looping on the kernel OOM-killer — 7+ restarts, repeated
`Memory cgroup out of memory: Killed process ... (gunicorn)
anon-rss:6261788kB` entries right at the 6G `MemoryMax` ceiling
(`DEPLOY.md`'s prior raise). A 502 is nginx's own response when the
upstream (gunicorn) is mid-restart or already dead — exactly what a
request landing during one of these kills would see.

Root cause, found by reading `app/clients/local_embedder.py`
(`EMBEDDER_FORCE_LOCAL` is still active — re-verified live via a real
`POST /v1/embeddings` call against Nebius, still `402
credit_balance_exhausted`, so the local CPU fallback can't be turned
off yet): `LocalEmbedderClient.embed()` tokenized and ran the model
over the **entire document's passage list in one single forward
pass** — `tokenizer(texts, padding=True, ...)` then one
`model(**encoded)` call, no batching. `padding=True` pads every
sequence in the batch to the longest one present, up to 512 tokens.
For the staged backlog's largest books (Huberman's *Protocols*, 671
pages; `Botanical Medicine for Women's Health`, 705 pages — both
specifically visible in the `staged_sources` backlog at crash time)
chunking produces thousands of passages; one unbatched CPU forward
pass over a batch that size needs activation memory scaling with
`batch_size × seq_len × hidden_dim × layers` — easily multiple
gigabytes, independent of `app/ingestion/queue.py`'s own concurrency
cap or the KG-extraction `ThreadPoolExecutor`'s worker count (this
call is synchronous and unrelated to either). This is the actual OOM
driver the `DEPLOY.md` `MemoryMax` raises (4G→6G, documented as a
mitigation, not a fix) were working around rather than fixing —
confirmed by the fact it recurred at the *new*, higher ceiling too.

Fixed: `embed()` now processes `texts` in fixed-size batches of 32,
accumulating results — peak memory per call now stays roughly
constant regardless of how many passages a document has, instead of
scaling linearly (worse, given quadratic-ish attention cost) with
document size.

## "Three dots do not open when clicked"

Reported directly, shortly after `v6.15`'s menu-open-by-default CSS
fix had already shipped and been verified correct in the compiled
output on the live server (re-checked: the deployed
`.menu-pop{...}` / `.menu-pop:popover-open{display:grid}` rules were
exactly as intended). Rather than chase a second guess at a CSS/
browser-support root cause with no way to reproduce or inspect the
reporting user's actual browser, `Menu.svelte` was rewritten outright
to drop its dependency on the native HTML `popover` attribute
entirely, in favor of explicit `$state`-driven open/close (a boolean
`open`, toggled on the trigger button's `onclick`, closed via a
capture-phase `document` click listener checking
`wrapEl.contains(e.target)`, plus an `Escape` keydown handler). This
removes any dependency on Popover API browser support — the same
code path now runs identically in every browser this app already
needs to support, with no feature-detection or fallback branch
needed, because there's nothing left to detect.

This menu now gates core per-document actions (Move, Delete, Private/
public toggle, Edit access, Assign/Reassign uploader) on every doc
row across Icons, List, *and* (since `v6.17`) Table view — a user who
can't open it loses access to most of the Library's per-document
admin actions entirely, not a cosmetic miss. "Guaranteed correct
everywhere" was judged worth more code than "fewer lines, relies on a
browser feature."

## What this does not change

- No change to `Menu.svelte`'s public API (`label`/`items` props,
  snippet-based item rendering) — every existing call site (admin
  Library's Icons/List/Table doc-card actions) needed zero changes.
- No change to `app/ingestion/queue.py`'s concurrency cap or the KG-
  extraction thread pool — neither was the actual cause here, despite
  being the natural first suspects given prior OOM history.
- `EMBEDDER_FORCE_LOCAL` stays on — Nebius billing is still exhausted
  (re-verified live). Turning it off (removing the local-embedder
  dependency entirely, the real long-term fix) requires funds landing
  on that account, out of this repo's control.
