"""One thin OpenAI-compatible client per AI-team role.

Every role is configured independently (base_url/model/api_key) so a
future deployment can point one role at a different provider without
touching any business logic that calls it — nothing in ingestion/,
retrieval/, or reasoning/ constructs a client or knows a base_url.

Base URLs are never hardcoded: every value here comes from
app.config.get_config(), which reads env vars (specs/v4.2, "config via
env vars / a settings file, do not hardcode base_urls").
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from openai import OpenAI

from ..config import get_config

cfg = get_config()


# A generation call must fail fast, not hang — found live: with max_tokens
# raised to 100_000 (to stop truncation crashes) and no request timeout,
# a slow/verbose response on a broad question left a traversal hop
# blocked on a raw socket read for 3+ minutes with no error, "running..."
# forever in the UI. 90s is generous for any of this app's real prompts
# (the largest observed real call — a full traversal judge on 20+
# candidates — finished in a few seconds) while still turning a genuine
# stall into a clean, fast openai.APIError instead of an indefinite hang.
_CHAT_TIMEOUT_SECONDS = 90.0


class Role(str, Enum):
    READER = "reader"
    GRAPH_BUILDER = "graph_builder"
    EMBEDDER = "embedder"
    ANSWER_ENGINE = "answer_engine"
    REASONER = "reasoner"
    # LLM-as-judge Checker (app/reasoning/llm_checker.py) — distinct from
    # the local HF-classifier Checker (app/reasoning/checker.py, cfg.
    # checker_model/checker_threshold), which isn't a chat role at all.
    CHECKER = "checker_llm"


@dataclass(frozen=True)
class RoleConfig:
    model: str
    base_url: str
    api_key: str


def _role_config(role: Role) -> RoleConfig:
    # Every role defaults to the shared Nebius endpoint (cfg.nebius_base_url
    # / cfg.nebius_api_key) but can be pointed elsewhere independently via
    # its own <ROLE>_BASE_URL / <ROLE>_API_KEY env var — see config.py.
    model, base_url, api_key = {
        Role.READER: (cfg.reader_model, cfg.reader_base_url, cfg.reader_api_key),
        Role.GRAPH_BUILDER: (cfg.graph_builder_model, cfg.graph_builder_base_url,
                             cfg.graph_builder_api_key),
        Role.EMBEDDER: (cfg.embedder_model, cfg.embedder_base_url, cfg.embedder_api_key),
        Role.ANSWER_ENGINE: (cfg.retrieval_model, cfg.retrieval_base_url, cfg.retrieval_api_key),
        Role.REASONER: (cfg.reasoner_model, cfg.reasoner_base_url, cfg.reasoner_api_key),
        Role.CHECKER: (cfg.checker_llm_model, cfg.checker_llm_base_url, cfg.checker_llm_api_key),
    }[role]
    return RoleConfig(model=model, base_url=base_url, api_key=api_key)


class LLMClient:
    """An OpenAI-compatible client bound to one AI-team role.

    Construction is cheap (no network call) and clients are safe to cache
    per-role at module level in callers — see get_client() below.
    """

    def __init__(self, role: Role):
        self.role = role
        self._rc = _role_config(role)
        self.model = self._rc.model
        self._client = OpenAI(base_url=self._rc.base_url, api_key=self._rc.api_key)

    def chat_json(self, system: str, prompt: str, schema: dict,
                  max_tokens: int = 100_000) -> tuple[dict, dict]:
        """One structured-output call. Returns (parsed_dict, usage).

        Retries once on a broken response — found live against Nebius, two
        distinct failure shapes from otherwise-healthy models on a strict
        json_schema call: empty content (no choice text at all), and
        truncated content (a real JSON string cut off mid-value by
        max_tokens before it closed, so json.loads() fails on the partial
        string). Both are provider/token-budget flakiness, not a
        malformed-schema problem, and a second attempt succeeds
        essentially every time — worth absorbing here once, not repeated
        as a retry loop at every one of chat_json's call sites.

        Bounded by _CHAT_TIMEOUT_SECONDS, same as ping_role() — found live:
        raising max_tokens to remove truncation (see that failure mode
        above) also removed the one thing that kept a verbose response
        bounded in wall-clock time. A traversal hop stuck 3+ minutes on
        "running..." with no error was this: nothing timed out, it was
        just still generating. A timeout turns that into a clean, fast
        openai.APIError instead of an indefinite hang.
        """
        import json

        def _call():
            response = self._client.with_options(timeout=_CHAT_TIMEOUT_SECONDS).chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "response", "schema": schema, "strict": True},
                },
            )
            return response.choices[0].message.content, response

        def _attempt():
            text, response = _call()
            if text is None:
                return None, None
            try:
                return json.loads(text), response
            except json.JSONDecodeError:
                return None, None

        parsed, response = _attempt()
        if parsed is None:
            parsed, response = _attempt()
        if parsed is None:
            raise ValueError(f"{self.model} ({self.role.value}) returned no usable JSON (twice)")
        return parsed, self._usage(response)

    def chat_text(self, system: str, prompt: str, max_tokens: int = 100_000,
                 extra_body: dict | None = None) -> tuple[str, dict]:
        """One free-text call. Returns (text, usage). Bounded by
        _CHAT_TIMEOUT_SECONDS — see chat_json's docstring.

        `extra_body` is a passthrough for provider/model-specific request
        fields — e.g. moonshotai/Kimi-K3 (Role.REASONER) needs
        {"thinking": {"type": "disabled"}} to skip its hidden chain-of-
        thought pass: found live, an *unset* thinking mode costs 30-120s+
        per call (reasoning_tokens in the raw response, invisible in the
        parsed text) for no visible quality difference on this app's
        prompts; disabled, the same call is ~1-2s. Caller's responsibility
        to know which models need which fields — this method stays a
        thin, generic passthrough rather than special-casing a model name.
        """
        response = self._client.with_options(timeout=_CHAT_TIMEOUT_SECONDS).chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            extra_body=extra_body,
        )
        text = (response.choices[0].message.content or "").strip()
        return text, self._usage(response)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in response.data]

    @staticmethod
    def _usage(response) -> dict:
        return {"input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens}


_clients: dict[Role, LLMClient] = {}


def get_client(role: Role) -> LLMClient:
    """Cached per-role singleton — avoids reconstructing an OpenAI client
    (and its underlying HTTP connection pool) on every call."""
    if role not in _clients:
        _clients[role] = LLMClient(role)
    return _clients[role]


# Every chat-model role that /api/health should report on individually.
# Named here (not just implied by the Role enum) so ping_all()'s output
# order is stable and every caller iterates the same list.
ALL_ROLES = (Role.READER, Role.GRAPH_BUILDER, Role.EMBEDDER,
            Role.ANSWER_ENGINE, Role.REASONER)


# A health check must fail fast, not hang — the openai SDK's default
# timeout is many minutes (tuned for a real generation call, not a
# credential probe), so a degraded/unreachable Nebius endpoint would
# otherwise make /api/health itself hang for that long instead of
# reporting "degraded" quickly. Found live: this exact hang, testing
# against a sandbox with no route to Nebius's real endpoint.
_PING_TIMEOUT_SECONDS = 8.0


def ping_role(role: Role) -> None:
    """Validate one role's credentials without spending tokens. Raises on
    failure — callers that want a non-raising per-role status (the health
    endpoint) should wrap this themselves, same as every other health
    check in app/main.py does via its own probe() helper.

    Lists models rather than retrieving the role's specific one — found
    live against the real Nebius endpoint: GET /models/{id} (models.retrieve)
    404s unconditionally, for every model id, even ones models.list() itself
    just returned; only the list endpoint is actually implemented there.
    """
    client = get_client(role)
    scoped = client._client.with_options(timeout=_PING_TIMEOUT_SECONDS)
    models = {m.id for m in scoped.models.list().data}
    if client.model not in models:
        raise ValueError(f"{client.model} ({role.value}) not found in the provider's model catalog")


def ping() -> bool:
    """Validate every chat-model role's credentials without spending
    tokens — kept as a single all-or-nothing check for callers that just
    want a bool (nothing in this codebase currently does, but it's the
    natural complement to ping_role()).

    Each of the 5 chat-model roles can independently override its own
    base_url/api_key (config.py's <ROLE>_BASE_URL/<ROLE>_API_KEY) — a
    health check that only probed one role (as this used to) would
    report "nebius: ok" even with a typo'd key for a different role,
    silently letting that role start failing in production undetected.
    See app/main.py's /api/health for the per-role breakdown instead.
    """
    for role in ALL_ROLES:
        ping_role(role)
    return True
