# v4.2 — LLM provider swap: Anthropic → Nebius (OpenAI-compatible)

**Status: spec only, not implemented.** A new version folder rather than a
v4.1 doc because this is a provider/data-model change to `app/llm.py` and
the AI pipeline's role structure, not a frontend IA/UX pass — per
[`specs/README.md`](../README.md)'s own rule ("a new version is cut when
there's a change worth auditing: new scope, a reversed decision, a
data-model change").

- [**01 · Provider swap and role mapping**](01-nebius-provider-swap.md) —
  what changes in `app/llm.py`, the five-model role mapping as given
  (superseding an earlier, less-detailed pass at the same mapping — see
  that doc's note), and the open questions that block implementation:
  most importantly, **no model in the given list covers the current
  Checker/verification role**, which is a safety-relevant gap, not a
  naming detail.

## What this does not change

Everything in [v4](../v4/README.md), [v4.1](../v4.1/README.md), and
transitively [v3](../v3/README.md) carries forward. This doc only touches
`app/llm.py`, its config (`READER_MODEL` etc.), and — pending the open
questions in 01 — possibly the practitioner-owned-API-key model
(`anthropic_api_key_encrypted`, the "Set your Anthropic key" onboarding
step touched by [v4.1/03 CR2](../v4.1/03-known-issues-and-gaps.md#cr2--the-practitioner-onboarding-checklist-can-never-show-not-done)).
