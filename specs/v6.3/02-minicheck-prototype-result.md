# MiniCheck-RoBERTa-Large prototype result — not adopted

`01`'s recommendation (prototype MiniCheck-RoBERTa-Large first) was acted
on the same day. The result is negative — this document records why the
swap was **not** shipped, so nobody re-derives the same dead end.

## What was tested

`app/reasoning/checker.py` was reimplemented against
`lytang/MiniCheck-RoBERTa-Large` (standard `AutoModelForSequenceClassification`
+ `AutoTokenizer`, no `trust_remote_code`, manual scoring — evidence and
sentence joined by the tokenizer's EOS token, softmax over the 2-way head,
index 1 = "supported", mirroring `github.com/Liyan06/MiniCheck`'s own
`Inferencer.inference()` without pulling in the `minicheck` pip package
or its `vllm` dependency). Same sub-batching (40 pairs/call) and
`_MAX_EVIDENCE_CHARS` truncation carried forward as defense-in-depth.

Run standalone on the production VPS (outside the systemd cgroup, same
practice used for the earlier HHEM OOM diagnosis) against a real
`general_lookup` → `reasoner.answer()` → `checker.check()` call, `CHECKER_MODEL`
overridden to the MiniCheck repo id for the test only — the live app's
config and `.env` were never touched.

## Result

```
lookup+reasoner: 17.66s, sentences=10, citations=10
checker.check(): 185.21s -> verdict=weak
peak RSS: 2521 MB
```

**185.21s for one `check()` call** — roughly 2.5-6.5x *slower* than
HHEM's already-too-slow 28-77s, and at a comparable-to-worse 2.5GB peak
RSS. This directly contradicts `01`'s estimate ("plausibly single-digit
seconds... unverified on this VPS specifically"). The likely cause:
this VPS's CPU-only inference is the actual bottleneck for *any*
transformer forward pass at this batch size (~110 evidence×sentence
pairs for a 10-citation answer), not something specific to HHEM's
architecture — a smaller, more standard model didn't buy the win `01`
expected, because the constraint is raw CPU throughput, not
architecture overhead.

A secondary, model-independent bug surfaced during this test: `_sentences()`
(`app/reasoning/checker.py`) splits on `.!?` alone, so Markdown section
headers like `## Answer` and `## Next steps` — introduced by the same
day's reasoner-prompt change to structured Markdown answers — get
treated as checkable "sentences" and predictably score as unsupported.
Worth fixing whenever the Checker's latency is actually solved; not
fixed here since it doesn't change this document's conclusion.

## What this changes

**Nothing shipped.** `app/reasoning/checker.py` and `app/config.py`
remain on HHEM-2.1-Open — reverted after this test, never touched on
the live production file (the test ran from an isolated scratch copy
of `app/`, using `.venv`'s installed `torch`/`transformers` but a
throwaway `CHECKER_MODEL` override, never the live `.env` or the live
`app/reasoning/checker.py`). `run_check` stays `false` by default,
unchanged from `specs/v6.3`'s trigger.

## Revised recommendation

Of `01`'s four candidates, this result weakens the case for **B**
(MiniCheck) as a fix and, by implication, for **A** (ONNX-exported HHEM)
and **C** (generic NLI cross-encoder) too — all three assume the
bottleneck is model choice or runtime overhead; this test suggests the
bottleneck is CPU-only inference itself on this VPS, which no same-class
local classifier swap is likely to fix. **D (small-LLM-as-judge via the
existing Nebius `Role` pattern)** becomes the more likely path forward —
it offloads inference to Nebius's own (presumably GPU-backed) infrastructure
instead of this VPS's CPU, sidestepping the constraint this test just
confirmed, at the cost of the weaker-guarantee tradeoff `01` already
flagged. Still unprototyped — this document only rules three things
out, it doesn't validate the fourth.
