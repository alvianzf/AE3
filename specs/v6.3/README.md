# v6.3 — Checker alternatives (lightweight/local + small-LLM fallback)

**Status: investigated, not implemented.** A new version folder rather
than appending to `v6.1`/`v6.2` (both released and not edited after the
fact) — same class of question (is there a cheaper way to do this), a
different pipeline stage: the anti-hallucination Checker
(`app/reasoning/checker.py`), not retrieval or ingestion.

**Trigger**: `run_check` now defaults to `false` in production
(2026-09-14) because HHEM-2.1-Open, even after the OOM fix (evidence
truncation + sub-batched `predict()`), still costs 28-77s on a real
single call — on top of an already-slow Reasoner step. The user asked
for research into smaller/faster local checkers, or a small LLM as a
last-measure substitute, so the safety feature can eventually come back
on by default without the latency cost that got it turned off.

- [**01 · Checker alternatives**](01-checker-alternatives.md) — four
  concrete candidates evaluated against the current HHEM-2.1-Open setup
  on this app's ~4GB-RAM production VPS: an ONNX-exported HHEM (same
  model, lighter runtime), MiniCheck-RoBERTa-Large (a purpose-built
  fact-checking classifier, smaller and faster, GPT-4-competitive per
  its own paper), a generic small NLI cross-encoder (smallest/fastest,
  least hallucination-specific), and a small-LLM-as-judge fallback via
  the existing Nebius `Role` pattern (zero local memory cost, offloads
  latency to the API instead). Recommendation: prototype MiniCheck first
  — closest fit to HHEM's actual job at a fraction of the size — with
  the small-LLM judge as the true "last measure" if no local classifier
  clears the latency bar.
- [**02 · MiniCheck prototype result — not adopted**](02-minicheck-prototype-result.md)
  — `01`'s recommendation was prototyped the same day. Result: **worse**,
  not better — 185.21s per real `check()` call (vs. HHEM's 28-77s) at a
  comparable-to-worse 2.5GB peak RSS. Reverted, nothing shipped. Points
  at CPU-only inference on this VPS as the real bottleneck, not model
  choice — which weakens the case for `01`'s other two local-model
  candidates too, and makes the small-LLM-as-judge fallback (offloads
  inference off this VPS entirely) the more promising unprototyped path.

## What this does not change

`app/reasoning/checker.py` and `app/config.py` remain on HHEM-2.1-Open —
the MiniCheck prototype in `02` ran from an isolated scratch copy and
was reverted, never landed on the live production file or its `.env`.
`run_check` stays `false` by default. Research and one same-day
prototype only, against the current `check()` contract in
`app/reasoning/checker.py` and the `Role` pattern in
`app/clients/llm_client.py` — written up for whoever prototypes the
small-LLM-judge fallback next.
