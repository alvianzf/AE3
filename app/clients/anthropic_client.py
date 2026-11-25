"""Anthropic-backed alternative to llm_client.LLMClient, for the five chat-
model roles (not Embedder — Anthropic has no embeddings endpoint).

Deliberately not routed through the openai SDK/Nebius's OpenAI-compatible
surface: Anthropic's own API (the Messages API) is a different shape, and
this calls it with the official `anthropic` SDK rather than an
OpenAI-compatible shim.

Matches LLMClient's call-site contract (chat_json/chat_text signatures,
.model attribute) so app/ingestion/pipeline.py, app/reasoning/reasoner.py,
app/reasoning/llm_checker.py and app/retrieval/traversal.py don't need to
know which provider they're talking to — see llm_client.get_client().
"""
from __future__ import annotations

import json
from typing import Callable

from anthropic import Anthropic

from ..config import get_config

cfg = get_config()

_CHAT_TIMEOUT_SECONDS = 90.0  # same budget as llm_client.LLMClient

# A health check must fail fast, not hang — same reasoning as
# llm_client.LLMClient.ping() (which scopes its own probe down from the
# generation-call timeout to this). Without it, ping() below inherited
# the 90s _CHAT_TIMEOUT_SECONDS from self._client, so a slow/unresponsive
# Anthropic endpoint made /api/health (and /api/admin/system-usage,
# which calls health() internally) hang for up to 90s per role with no
# error — on the admin Settings page (the only page whose load() awaits
# both of those), that's a page that appears to just hang/stay blank
# rather than fail visibly.
_PING_TIMEOUT_SECONDS = 8.0  # same budget as llm_client.LLMClient

# Real per-model output-token ceilings — found live: app/retrieval/
# traversal.py's relevance judge calls chat_json(max_tokens=100_000) for
# Role.ANSWER_ENGINE, which maps to Haiku 4.5 here; Anthropic rejected it
# outright (a BadRequestError, not a truncation) with "max_tokens: 100000
# > 64000, which is the maximum allowed number of output tokens for
# claude-haiku-4-5-20251001". Every call site's max_tokens has to be
# clamped per-model rather than trusted as-is, same reasoning
# llm_client.LLMClient's chat_json() docstring already gives for Nebius's
# dedicated Qwen3-32B deployment capping at 40_960.
_MAX_OUTPUT_TOKENS = {
    "claude-haiku-4-5-20251001": 64_000,
    "claude-sonnet-5": 128_000,
    "claude-opus-5": 128_000,
}


def _cacheable_system(system: str) -> list[dict]:
    """specs/v9/01 (candidate A): every call site here passes a static,
    per-role system prompt reused across many calls within the same
    role (RELEVANCE_SYSTEM once per traversal hop, CHECK_SYSTEM once per
    consult, REASONER_SYSTEM once per consult and again on a retry,
    KG_BUILDER_SYSTEM/READER_SYSTEM once per ingest) — marking it
    ephemeral-cacheable lets Anthropic skip reprocessing those tokens on
    a cache hit within the TTL, measurably faster and cheaper than a
    full read, with zero change to the prompt, model, or output. Below
    Anthropic's per-model minimum cacheable length, cache_control is
    simply a no-op, not an error, so this is safe to apply unconditionally
    rather than special-casing short prompts."""
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


def _move_cache_breakpoint(messages: list[dict]) -> None:
    """chat_agentic()'s multi-turn loop only: keeps exactly one 'growing
    tail' cache breakpoint, on the last content block of the most recent
    message, moved forward each turn rather than left stacking — the
    second half of Anthropic's documented agent-loop caching pattern
    (the first half, the system+tools prefix, is `_cacheable_system`'s own
    permanent breakpoint). Clearing the previous turn's marker before
    adding the new one keeps this to 2 breakpoints total for the whole
    loop (system + tail), comfortably under Anthropic's 4-breakpoint
    limit regardless of max_turns — stacking a new one every turn instead
    would exceed it by turn 5.

    Every message by the time this runs is already a plain dict with
    `content` as a list of plain dict blocks (chat_agentic() builds them
    that way specifically so this can mutate them) — this function would
    silently no-op on an SDK response-block object, which has no
    `cache_control` field to set, so that conversion has to happen first,
    not here."""
    for m in messages[:-1]:
        content = m.get("content")
        if isinstance(content, list) and content:
            content[-1].pop("cache_control", None)
    content = messages[-1].get("content")
    if isinstance(content, list) and content:
        content[-1] = {**content[-1], "cache_control": {"type": "ephemeral"}}


class AnthropicLLMClient:
    def __init__(self, role, model: str):
        self.role = role
        self.model = model
        self._client = Anthropic(api_key=cfg.anthropic_api_key, timeout=_CHAT_TIMEOUT_SECONDS)

    def _clamp(self, max_tokens: int) -> int:
        cap = _MAX_OUTPUT_TOKENS.get(self.model)
        return min(max_tokens, cap) if cap else max_tokens

    def chat_json(self, system: str, prompt: str, schema: dict,
                  max_tokens: int = 20_000, extra_body: dict | None = None) -> tuple[dict, dict]:
        """Structured output via forced strict tool-use — the schemas this
        app already defines (plain JSON Schema with additionalProperties:
        false + required) drop straight in as a tool's input_schema.
        `extra_body` (Nebius/OpenAI's thinking-disable knob) is accepted
        for call-site compatibility but ignored: thinking is explicitly
        disabled below instead, since a forced tool_choice already
        guarantees a tool_use response — no need for the model to think
        through format, only through the extraction itself, and disabling
        it here keeps these calls fast."""
        tool = {
            "name": "emit",
            "description": "Return the result.",
            "input_schema": schema,
            "strict": True,
        }

        # Haiku 4.5 defaults to no thinking already (it doesn't take the
        # adaptive-family {"type": "disabled"} value) — only the
        # adaptive-thinking models (Opus 5/Sonnet 5) need it said explicitly.
        kwargs = {"thinking": {"type": "disabled"}} if "haiku" not in self.model else {}

        def _attempt():
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self._clamp(max_tokens),
                system=_cacheable_system(system),
                messages=[{"role": "user", "content": prompt}],
                tools=[tool],
                tool_choice={"type": "tool", "name": "emit"},
                **kwargs,
            )
            for block in response.content:
                if block.type == "tool_use" and block.name == "emit":
                    return block.input, response
            return None, response

        parsed, response = _attempt()
        if parsed is None:
            parsed, response = _attempt()
        if parsed is None:
            raise ValueError(f"{self.model} ({self.role.value}) returned no tool_use block (twice)")
        usage = self._usage(response)
        try:
            from app.token_tracker import record_tokens
            record_tokens(self.role, usage.get("input_tokens", 0), usage.get("output_tokens", 0), self.model)
        except Exception:
            pass
        return parsed, usage

    def chat_text(self, system: str, prompt: str, max_tokens: int = 100_000,
                 extra_body: dict | None = None) -> tuple[str, dict]:
        """Free-text call. Thinking is left at its model default (adaptive
        on Opus 5/Sonnet 5) only for Role.REASONER — unlike chat_json
        above, there's no forced tool_choice to conflict with, and this is
        exactly the kind of call (Role.REASONER's final answer /
        generate_session_document) where letting the model think pays for
        itself in quality. Every other chat_text caller (Role.CHECKER/
        Role.READER restating already-known data, not forming a new
        judgment) passes extra_body=NO_THINKING same as chat_json's
        callers do — honored here by role rather than silently dropped,
        so it isn't paying Sonnet 5's adaptive-thinking latency for a call
        that doesn't benefit from it, the same waste llm_client.NO_THINKING
        exists to avoid on the Nebius side."""
        kwargs = {} if self.role.value == "reasoner" else {"thinking": {"type": "disabled"}}
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self._clamp(max_tokens),
            system=_cacheable_system(system),
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        usage = self._usage(response)
        try:
            from app.token_tracker import record_tokens
            record_tokens(self.role, usage.get("input_tokens", 0), usage.get("output_tokens", 0), self.model)
        except Exception:
            pass
        return text, usage

    def chat_vision(self, system: str, media_type: str, image_b64: str,
                    prompt: str = "Transcribe this image.", max_tokens: int = 8_000) -> tuple[str, dict]:
        """One image-in, text-out call — scanned-PDF-page and photographed-
        document OCR (app/ingestion/ocr.py) is the only caller. No
        chat_json equivalent: OCR wants free-text transcription, not a
        structured field, and there's no other vision call site in this
        app to generalize for yet."""
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self._clamp(max_tokens),
            system=_cacheable_system(system),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
            thinking={"type": "disabled"},
        )
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        usage = self._usage(response)
        try:
            from app.token_tracker import record_tokens
            record_tokens(self.role, usage.get("input_tokens", 0), usage.get("output_tokens", 0), self.model)
        except Exception:
            pass
        return text, usage

    def chat_text_stream(self, system: str, prompt: str, max_tokens: int = 100_000,
                         extra_body: dict | None = None):
        """Same contract as llm_client.LLMClient.chat_text_stream — see
        that docstring. Thinking is left at its model default for
        Role.REASONER (this method's only real caller), same reasoning
        chat_text already gives; the SDK's `text_stream` helper yields
        only real text-block deltas, never a thinking block's own delta
        text, so a thinking pass (if one runs) never leaks into the
        answer the practitioner sees streaming in."""
        kwargs = {} if self.role.value == "reasoner" else {"thinking": {"type": "disabled"}}
        with self._client.messages.stream(
            model=self.model, max_tokens=self._clamp(max_tokens),
            system=_cacheable_system(system), messages=[{"role": "user", "content": prompt}],
            **kwargs,
        ) as stream:
            for text in stream.text_stream:
                yield "delta", text
            final = stream.get_final_message()
        usage = self._usage(final)
        self._record_usage(usage)
        yield "done", usage

    def chat_agentic(self, system: str, prompt: str, tools: list[dict],
                     tool_fn: Callable[[str, dict], dict], max_turns: int = 6,
                     extra_body: dict | None = None) -> tuple[dict | None, list[dict], dict]:
        """See llm_client.LLMClient.chat_agentic's docstring — same
        contract, Anthropic's native multi-turn tool-use shape instead of
        OpenAI's. `tools` already matches Anthropic's own
        {"name", "description", "input_schema"} shape (that's why
        app/retrieval/agentic.py's TOOLS uses this naming as the shared,
        provider-neutral shape), so no translation is needed here, unlike
        the OpenAI-compatible side.

        tool_choice is left at its default ("auto"), unlike chat_json's
        forced single tool_use — the whole point of this loop is letting
        the model decide whether it needs another tool call or is ready
        to submit_answer. Thinking is left enabled for Role.REASONER
        (this method's only real caller), same reasoning chat_text
        already gives — the model benefits from reasoning about whether
        it has enough evidence, this isn't a fixed-format extraction call.

        Incremental prompt caching on the growing message history (found
        live, 2026-11-25: turn N was reprocessing turns 1..N-1 as fresh,
        uncached tokens every single turn — the dominant cost of a 6-7
        turn loop running slower than the pipeline it's meant to replace,
        per this session's architecture-latency research). `_cacheable_
        system()` already gives the static system+tools prefix one
        explicit, permanent breakpoint; `_move_cache_breakpoint` below adds
        a second, *moving* one at the end of the growing tail each turn —
        Anthropic's documented combination for agent loops — so turn N
        reads turns 1..N-1 from cache and only pays full price for
        whatever's new this turn. Every message is built as plain dicts
        (not the SDK's response.content objects passed straight through)
        specifically so a cache_control key can be attached/removed on
        them each turn.
        """
        anthropic_tools = [
            {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in tools
        ]
        messages: list[dict] = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        trace: list[dict] = []
        total_usage = dict(input_tokens=0, output_tokens=0)
        kwargs = {} if self.role.value == "reasoner" else {"thinking": {"type": "disabled"}}

        for _turn in range(max_turns):
            _move_cache_breakpoint(messages)
            response = self._client.messages.create(
                model=self.model, max_tokens=self._clamp(20_000),
                system=_cacheable_system(system), messages=messages,
                tools=anthropic_tools, **kwargs,
            )
            usage = self._usage(response)
            total_usage["input_tokens"] += usage["input_tokens"]
            total_usage["output_tokens"] += usage["output_tokens"]
            assistant_content = [block.model_dump() for block in response.content]
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                # Same nudge llm_client.LLMClient.chat_agentic gives a
                # model that answered in plain text instead of calling a
                # tool — see that docstring.
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": [{"type": "text", "text":
                                 "Call a tool — search for more evidence, or submit_answer "
                                 "if you have enough."}]})
                continue
            messages.append({"role": "assistant", "content": assistant_content})
            tool_results = []
            for block in tool_uses:
                if block.name == "submit_answer":
                    self._record_usage(total_usage)
                    return block.input, trace, total_usage
                try:
                    output = tool_fn(block.name, block.input)
                except Exception as exc:
                    # Same reasoning as llm_client.LLMClient.chat_agentic —
                    # a tool execution error must reach the model as a
                    # reactable tool result, not kill the loop.
                    output = {"error": str(exc)}
                trace.append({"tool": block.name, "input": block.input, "output": output})
                tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                     "content": json.dumps(output)})
            messages.append({"role": "user", "content": tool_results})
        self._record_usage(total_usage)
        return None, trace, total_usage

    def _record_usage(self, usage: dict) -> None:
        try:
            from app.token_tracker import record_tokens
            record_tokens(self.role, usage.get("input_tokens", 0), usage.get("output_tokens", 0), self.model)
        except Exception:
            pass

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Anthropic has no embeddings endpoint — Role.EMBEDDER always "
            "stays on Nebius regardless of the llm_provider setting."
        )

    def ping(self) -> None:
        """Validate credentials without spending tokens — same reasoning
        as llm_client.LLMClient.ping(): list models rather than retrieve
        the role's specific one."""
        scoped = self._client.with_options(timeout=_PING_TIMEOUT_SECONDS)
        models = {m.id for m in scoped.models.list()}
        if self.model not in models:
            raise ValueError(f"{self.model} ({self.role.value}) not found in the provider's model catalog")

    @staticmethod
    def _usage(response) -> dict:
        return {"input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens}
