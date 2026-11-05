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

from anthropic import Anthropic

from ..config import get_config

cfg = get_config()

_CHAT_TIMEOUT_SECONDS = 90.0  # same budget as llm_client.LLMClient

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
        on Opus 5/Sonnet 5) rather than forced off — unlike chat_json
        above, there's no forced tool_choice to conflict with, and this is
        exactly the kind of call (Role.REASONER's final answer) where
        letting the model think pays for itself in quality."""
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self._clamp(max_tokens),
            system=_cacheable_system(system),
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        usage = self._usage(response)
        try:
            from app.token_tracker import record_tokens
            record_tokens(self.role, usage.get("input_tokens", 0), usage.get("output_tokens", 0), self.model)
        except Exception:
            pass
        return text, usage

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Anthropic has no embeddings endpoint — Role.EMBEDDER always "
            "stays on Nebius regardless of the llm_provider setting."
        )

    def ping(self) -> None:
        """Validate credentials without spending tokens — same reasoning
        as llm_client.LLMClient.ping(): list models rather than retrieve
        the role's specific one."""
        models = {m.id for m in self._client.models.list()}
        if self.model not in models:
            raise ValueError(f"{self.model} ({self.role.value}) not found in the provider's model catalog")

    @staticmethod
    def _usage(response) -> dict:
        return {"input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens}
