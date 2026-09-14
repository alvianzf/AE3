# LLM-as-judge Checker — implemented, `run_check` back on by default

`02` ruled out local-model swaps (MiniCheck, and by implication ONNX-HHEM
and a generic NLI cross-encoder) because the bottleneck is this VPS's
CPU-only inference, not model choice. `01`'s fourth candidate — a
small-LLM-as-judge via the existing `Role` pattern, which offloads
scoring to Nebius instead of this VPS — was prototyped and shipped the
same day.

## What was built

`app/reasoning/llm_checker.py` (new): one batched `chat_json` call to a
new `Role.CHECKER` (default model `Qwen/Qwen3-30B-A3B-Instruct-2507`,
same one already proven for `traversal.py`'s per-hop relevance judge)
that judges every answer sentence against every cited passage at once —
same "one batched call, not one per pair" pattern the relevance judge
already uses, and the reason this is a single ~2-6s round-trip instead
of something that scales with sentences × evidence. Same contract as
the HHEM path's `check()` (`verdict`/`unsupported`/`note`), plus a
`usage` key the HHEM path doesn't have (a real token spend, unlike a
local classifier call). Also fixes a bug the HHEM path still has:
`_sentences()` here skips Markdown headers (`## Answer` etc.) so the
same-day structured-answer prompt change doesn't get its own section
headings scored as unsupported "sentences".

`app/main.py`'s `/api/me/consult` now calls `llm_checker.check()`
instead of `checker.check()` (both retry-path calls). `MeConsult.
run_check` defaults back to `true` — off since the HHEM latency finding
earlier the same day, back on now that a real per-call cost is
consistently single-digit seconds.

## Verified live

Two real consult questions run against production: 1.2-5.03s/call in
an isolated test, 6.46s/call against the actual deployed
`/opt/clinic` code post-deploy. Down from HHEM's 28-77s and MiniCheck's
185s.

## What this does not change

`app/reasoning/checker.py` (the local HHEM classifier) is untouched —
still there, still selectable by swapping the import back in
`app/main.py`, not deleted. This is a default swapped, not a design
committed to permanently: an LLM judging another LLM's output is a
philosophically weaker guarantee than a classifier trained specifically
for this, a tradeoff `01` flagged going in. If verdicts ever feel
unreliable in practice, that one-line import swap is the way back, not
a rewrite.
