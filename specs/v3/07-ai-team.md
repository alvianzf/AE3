# 07 · The AI team

The five core roles, plus the two on-demand roles, are unchanged from v1
([v1/03-ai-team.md](../v1/03-ai-team.md)) and the key-billing split is
unchanged from v2 ([v2/07-ai-team.md](../v2/07-ai-team.md)). What changes in
v3 is two things found by a PM/Analyst/Architect review of the pipeline
([CHANGELOG](../CHANGELOG.md#v3)): the Checker's verdict gets one bounded
consequence instead of none, and the Summariser goes from fully-implemented
dead code to a reachable feature.

## What did not change, and why

The review's headline finding: **do not make the seven roles chatty.** The
product's actual value is that a fixed pipeline with function-argument
boundaries is auditable — the Librarian's ignorance of source grades, for
instance, is enforced in code (`select_sources()` never receives the field),
not by prompt discipline. A general agent-to-agent messaging layer would put
that boundary at risk, complicate the v2 per-role API-key billing (which
call tree spent which tenant's money becomes harder to trace once calls can
fan out dynamically), and turn a bounded, documented cost/latency shape (3-4
calls, ~40s) into an unbounded one. Two frameworks were considered
(LangGraph, CrewAI) and rejected for the same reason: disproportionate for a
seven-function, single-file, hand-auditable pipeline. See the review notes
linked from the changelog for the full reasoning.

## New: bounded Checker → Specialist retry

Previously, a `weak` verdict from the Checker was terminal — the flawed
answer shipped to the practitioner with a badge, and the specific
`unsupported` claims it had already identified were never acted on.

Now, exactly once per question:

1. Specialist answers, Checker checks.
2. If `verdict == "weak"`, the Specialist is called a second time with the
   same passages, the same instructions, plus the `unsupported` claim list
   and an instruction to either ground each one in a cited passage or drop
   it.
3. The Checker checks the revised answer once more.
4. Whichever answer has the better verdict is shown (revised if it improved
   to `pass` or reduced the `unsupported` count; original otherwise) —
   always with its own verdict, never a blended one. The response now
   carries a `revised: bool` flag alongside `verdict` so the UI can say "the
   first draft was revised after an internal check" rather than silently
   swapping text.

This is a hard cap of one retry, enforced in the route handler
(`app/main.py`), not something either model can extend — the point is to
close the one gap the review found evidence for, not to open a general
revise-until-satisfied loop. Two extra calls in the worst case (Specialist +
Checker again), so the documented cost/latency ceiling moves from "3-4 calls,
~40s" to "5-6 calls, ~70s" in the `weak` case only; the common `pass` case is
unchanged.

**The retry's instruction is explicitly "ground it or drop it," never
"make it sound supported."** The revision prompt gives the Specialist the
same passages as the first attempt — no new sources, no permission to
paraphrase a passage more loosely to make it appear to cover a claim it
doesn't. If the second Checker pass still finds unsupported claims, that
answer still ships as `weak` with its own (possibly shorter) unsupported
list — the retry is one bounded attempt at grounding, not a guarantee of a
clean pass, and this version does not add a second retry or any other
mechanism to force one. This is the same no-fabrication invariant the
Specialist/Checker pair already enforces in v1/v2 ([v1/03-ai-team.md](../v1/03-ai-team.md));
the retry is scoped so it cannot weaken it.

## New: Summariser is reachable

`summarize_session()` has existed in `app/llm.py` since v1, is documented in
the v1 spec, and was never wired to a route — an orphaned feature, not a
deferred one. v3 adds `POST /api/me/clients/{id}/sessions/{session_id}/summary`
([08](08-api.md)), which runs the Summariser against that session's turns and
saves the result as a `session_summary` vault entry (the entry kind already
existed in `vault.py`, also unused). No new LLM role, no new prompt — this is
closing a gap between what was built and what was reachable.

## New: live progress is visible per call

**Unverified against this codebase, flagging rather than asserting:** the
Anthropic Messages API's response contract is documented to include a
`usage: {input_tokens, output_tokens}` object on every call. Checked
directly against `app/llm.py`'s three `messages.create()` call sites
(lines 27, 450, 523) — none of them currently reads `.usage` off the
response, so whether it's present on the SDK/API version this project pins
is not confirmed here. `POST /api/me/consult` reports which role is
currently running and, if the field is present, that role's token usage,
via a live stream ([08](08-api.md#live-progress-stream)), rendered as a
toast in the practitioner UI ([15](15-design-system.md#live-agent-toast)).
[TODO.md](TODO.md) lists confirming `usage`'s presence (against the pinned
SDK version, not assumed) as the first implementation step for this
feature — the role-name/status half of the toast does not depend on it and
should ship regardless of the outcome.

## Everything else

Model choices (Haiku for Reader/Indexer/Checker, Sonnet for
Librarian/Consolidator, Opus for Specialist), the no-match refusal path, the
Librarian/grade boundary, and the per-role API-key billing split all carry
forward unchanged from v1/v2. Not repeated here to avoid drift between
documents describing the same unchanged behavior.
