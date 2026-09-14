# Hallucination on topic-adjacent context, and two citation bugs

## The bug

A real question against a real client's session: "What dietary changes
would help with the reported bloating?" The accumulated context
contained nothing about bloating or diet specifically — sleep-hygiene
guidance, PCOS/metformin literature, time-restricted-eating advice.
None of it addressed the actual question. The Reasoner answered anyway,
constructing dietary advice by extrapolating from the nearby-but-not-
on-point context instead of saying the library had nothing on it.

`REASONER_SYSTEM` (`app/reasoning/reasoner.py`) already said "If the
context does not cover the question, say so plainly... Never fill a
gap from general knowledge" — true in spirit, but too weak in practice:
it didn't say what "covers the question" means, so a model that found
topic-adjacent passages could reasonably read that instruction as
satisfied and extrapolate a plausible answer from them.

## The fix

Added an explicit rule: a passage that is merely topic-adjacent does
NOT count as covering the question. No answer may be built by
inference or extrapolation from nearby context — only from a passage
that directly and specifically addresses what was asked. Also made the
"cite every claim" rule explicit about the converse: an uncited claim
is a claim with no evidence, and shouldn't exist.

**Verified live against production** (isolated scratch copy of `app/`,
same practice as the Checker OOM diagnosis and the MiniCheck
prototype — never touched the live `.env` or the live `app/reasoning/
reasoner.py`): the same question now opens with "The knowledge base
has no direct guidance on dietary changes for bloating," names the
topic-adjacent sources that exist without claiming they answer the
question, and moves on to what a practitioner would need to ask
instead of fabricating a plan.

## Two citation bugs found while verifying the fix

Both stem from the same wrong assumption: that the Reasoner always
cites one source per bracket (`[K1]`, `[K2]`, ...). In practice it
sometimes groups several into one bracket (`[K1, K3]`) — real output,
seen during the live verification above.

1. **`app/main.py`'s `sources` list included every node the traversal
   retrieved and kept**, not just the ones the answer actually cited —
   `traversal.accumulated` in full, regardless of whether the Reasoner
   referenced a given node. This implied more of the answer was sourced
   than actually was, and directly contradicts what "Sources" should
   mean. Fixed: `sources` is now filtered to only the K-indices that
   appear anywhere in `answer_text`.

2. **That citation check itself (and the client-side citation-button
   renderer, `web/src/lib/markdown.ts`) only matched a single-citation
   bracket shape** (`"[K1]" in answer_text`, `/\[([SK]\d+)\]/g`) — a
   grouped bracket like `[K1, K3]` doesn't contain the literal
   substring `"[K1]"` or `"[K3]"`, so both the source-filter and the
   citation-to-button conversion silently missed every citation inside
   a grouped bracket. Fixed on both sides: extract every `K`-number
   out of *any* bracket group (`re.findall(r"K(\d+)", ...)` server-
   side; a bracket-group regex that splits on comma and re-attaches
   the group's letter prefix client-side), not just an exact single-
   citation match.

## What this does not change

The retrieval pipeline (seed search, traversal, `general_lookup`) is
untouched — this is a Reasoner prompt fix plus a citation-parsing fix,
not a change to what context gets retrieved. The Checker (`v6.3`'s
LLM-as-judge) should, in principle, have caught the original
hallucination too (an unsupported sentence should score `weak`) — not
independently re-verified here, since the prompt fix removes the
hallucination at its source; worth revisiting if a similar case
appears with the Checker on and this prompt fix in place.
