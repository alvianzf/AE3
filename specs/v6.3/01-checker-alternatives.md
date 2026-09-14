# Checker alternatives

## Current interface (must stay compatible)

`app/reasoning/checker.py::check(question, reasoned, patient_context_text) -> dict`:

```python
{"verdict": "pass" | "weak", "unsupported": [str, ...], "note": str}
```

Internally: split the answer into sentences, build `(evidence, sentence)`
pairs (each cited node's text + the patient-context text, truncated to
700 chars, against every answer sentence), score all pairs, flag a
sentence "unsupported" if its best-matching evidence still scores below
`cfg.checker_threshold` (0.5). Any replacement needs a `predict()`-shaped
scoring call (or an equivalent per-pair judgment) to slot into this loop
without changing `check()`'s shape — or needs `check()` itself rewritten,
which is a bigger, separate change.

## Current cost baseline (HHEM-2.1-Open, `vectara/hallucination_evaluation_model`)

- Model: T5-based sequence classifier, `trust_remote_code=True`, loaded via
  `transformers.AutoModelForSequenceClassification`. Real max sequence
  length 512 tokens.
- Measured live (2026-09-14 Reasoner/Checker audit): 28-77s for a single
  real `check()` call post-OOM-fix, dominated by CPU inference cost on
  this VPS (no GPU) plus `transformers`'s per-call overhead — not model
  download (that's a one-time, already-amortized cost after first load).
- Package cost: `transformers` + `torch` (CPU wheel) together are roughly
  600MB-1GB+ of installed dependencies, and `torch` alone reserves a
  meaningful chunk of resident memory just from being imported, before
  any inference runs.
- Prior failure mode (now fixed, see `app/reasoning/checker.py`'s own
  comments): peak memory scaled worse than linearly with total batch
  size, root-caused to `trust_remote_code=True` not truncating
  gracefully past 512 tokens; fixed by evidence-text truncation (700
  chars) and 40-pair sub-batching. `MemoryMax` raised 500M→4G as a
  standing safety margin, not fully undone by the code fix.

## Candidates

### A. ONNX-exported HHEM (same model, lighter runtime)

Vectara publishes an ONNX export of HHEM-2.1 alongside the PyTorch
checkpoint, runnable via `onnxruntime` instead of `torch` +
`transformers`'s full forward-pass machinery. Same weights, same
accuracy — the win is purely inference-engine overhead: ONNX Runtime's
CPU execution provider is typically 2-4x faster than eager PyTorch for
small-to-mid transformer models on CPU, with a materially smaller
dependency footprint (`onnxruntime` alone is tens of MB, vs. `torch`'s
several hundred).

- **Latency**: likely cuts real per-call time to roughly 10-25s (rough,
  unverified estimate scaled from ONNX Runtime's typical CPU speedup on
  comparable-sized encoder-decoder models) — still not fast, because the
  root cost here is CPU-only inference on a VPS with no GPU, not just
  runtime overhead.
- **Memory**: meaningfully lower peak RSS than the current `torch`
  import alone, likely bringing real headroom back under a 1-2GB
  `MemoryMax` instead of needing 4G.
- **Risk**: needs Vectara's ONNX artifact to actually exist and match
  the currently-pinned model version, and a rewrite of `_get_checker_model()`
  / `check()`'s scoring call to use `onnxruntime` + manual tokenization
  instead of `model.predict()`'s convenience wrapper — more integration
  work than a drop-in swap.
- **Verdict**: same accuracy, real but unverified speed win, more
  integration effort than it first looks.

### B. MiniCheck (RoBERTa-Large checkpoint, `lytang/MiniCheck-RoBERTa-Large`)

MiniCheck (Tang et al., 2024) is a fact-checking/grounding classifier
purpose-built for exactly this job — "does this sentence follow from
this evidence" — distilled from GPT-4-generated training data down to
small checkpoints (RoBERTa-Large ≈355M params is the smallest; a 7B
variant also exists but is the wrong direction for this VPS). The
paper's own claim is GPT-4-competitive fact-checking accuracy at a
fraction of the cost, validated across several factual-consistency
benchmarks.

- **Latency**: RoBERTa-Large-class encoder, no autoregressive decoding —
  materially faster per pair than HHEM's T5-based encoder-decoder scoring,
  plausibly single-digit seconds for a realistic batch of evidence×sentence
  pairs on CPU (unverified on this VPS specifically; needs a real
  benchmark before trusting the number).
- **Memory**: ~355M params is smaller than HHEM's own footprint, and it's
  a standard `transformers` sequence-classification model (no
  `trust_remote_code` custom forward pass) — the exact bug class that
  caused the OOM (ungraceful truncation past max length) is far less
  likely with a stock architecture, though truncation still needs to be
  handled explicitly in the integration code as defense-in-depth.
  Same `torch`+`transformers` dependency cost as today, no new package
  category.
- **Risk**: still needs its own live latency/memory benchmark on this
  VPS before trusting it in production (nothing here has been run — this
  is research, not a completed prototype); slightly different output
  shape than a raw `predict()` call (MiniCheck's reference usage returns
  a support probability + explanation, needs mapping onto the existing
  `unsupported: list[str]` shape).
- **Verdict**: closest fit to HHEM's actual job, smaller model, real
  published accuracy validation, standard (non-custom) architecture —
  best first prototype candidate.

### C. Generic small NLI cross-encoder (`cross-encoder/nli-deberta-v3-small`, ~140M)

A general-purpose natural-language-inference model (entailment/neutral/
contradiction), not purpose-built for hallucination detection, but
usable here by treating "evidence entails sentence" as the pass signal
and thresholding the entailment probability. Much smaller than either
HHEM or MiniCheck (~140M params), well-established `sentence-transformers`
`CrossEncoder` API, fast on CPU.

- **Latency**: the fastest of the local candidates — small encoder-only
  model, sub-second to low-single-digit seconds for a realistic batch,
  plausible even on this VPS's CPU (still unverified, no benchmark run).
- **Memory**: smallest footprint of the local candidates.
- **Risk**: real accuracy risk — general NLI training data (SNLI/MNLI)
  is short, clean sentence pairs, not clinical prose against a 700-char
  evidence chunk; this is the candidate most likely to either over-flag
  (many true claims don't look like classic "entailment" phrasing) or
  under-flag (fluent-but-unsupported clinical claims can still score as
  plausible entailment). No published validation for this specific
  hallucination-detection use case, unlike A/B.
- **Verdict**: worth keeping in mind as the cheapest fallback if B turns
  out too slow, but shouldn't be the first thing prototyped — accuracy
  risk is unquantified and clinical-safety-relevant.

### D. Small LLM as judge (last-measure fallback, via existing `Role` pattern)

Instead of any local classifier, add a judge call through the existing
Nebius token-factory pattern in `app/clients/llm_client.py` (same shape
as `Role.ANSWER_ENGINE`'s per-hop relevance judgments in
`app/retrieval/traversal.py`) — prompt a small, fast instruct model with
each `(evidence, sentence)` pair (or a smarter single-batched prompt
covering many sentences at once against their citations) and a strict
JSON schema (`{"supported": bool}`), reusing `chat_json`'s existing
retry/timeout handling.

- **Latency**: depends entirely on model choice and batching strategy.
  A single well-designed multi-sentence-at-once prompt (rather than one
  call per evidence×sentence pair) plausibly lands in the 2-5s range —
  in the same ballpark as this session's other non-reasoning Nebius
  calls (seed search ~1s, per-hop traversal judgments a few seconds
  each). Naive one-call-per-pair would be far slower and is not the
  right design.
- **Memory**: zero local memory or dependency cost — no `torch`, no
  model download, nothing added to `MemoryMax` pressure. This is the
  one candidate that doesn't compete with the app's own RAM budget at
  all.
- **Risk**: an LLM judging its own kind of output is a known weaker
  guarantee than a purpose-built classifier trained specifically to
  catch this failure mode — the entire reason a dedicated Checker
  (HHEM) was chosen originally (specs/v4.2's decision to keep the
  Checker as a direct classifier call, not a chat completion). Costs a
  real API call per consult (money + Nebius rate limits) instead of a
  one-time local model load. Best treated as the explicit "last
  measure" the user asked for, not the first choice.
- **Verdict**: the right fallback if B and C both fail to clear a real
  latency/accuracy bar in prototyping — free of the VPS's memory
  constraints entirely, reuses a pattern already proven reliable
  elsewhere in this codebase, but a philosophically weaker safety
  guarantee than a dedicated classifier.

## Recommendation

Prototype **B (MiniCheck-RoBERTa-Large)** first. It's the only candidate
that's both purpose-built for this exact task (unlike C and D) and
meaningfully smaller/faster than the current model (unlike A, which
keeps HHEM's own cost profile and just trims runtime overhead). Concretely:
load `lytang/MiniCheck-RoBERTa-Large` behind the same lazy-singleton
pattern `_get_checker_model()` already uses, benchmark real latency and
peak RSS on the production VPS with the same truncation/sub-batching
defenses ported over defensively, and compare its `unsupported` output
against HHEM's on a handful of real consults before considering a swap.

Keep **D (small-LLM judge)** as the documented fallback if B doesn't
clear a usable latency bar in practice — it needs no VPS memory budget
at all, which makes it the safest "last measure" the user asked for,
even though it's the philosophically weaker guarantee of the four.

**Not recommended as a first move**: A (real but modest, unverified win
for real integration cost) and C (cheapest but accuracy-unvalidated for
this specific clinical-safety use case).
