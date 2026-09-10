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


class Role(str, Enum):
    READER = "reader"
    GRAPH_BUILDER = "graph_builder"
    EMBEDDER = "embedder"
    ANSWER_ENGINE = "answer_engine"
    REASONER = "reasoner"


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
                  max_tokens: int = 2000) -> tuple[dict, dict]:
        """One structured-output call. Returns (parsed_dict, usage)."""
        import json
        response = self._client.chat.completions.create(
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
        text = response.choices[0].message.content
        if text is None:
            raise ValueError(f"{self.model} ({self.role.value}) returned no content")
        return json.loads(text), self._usage(response)

    def chat_text(self, system: str, prompt: str, max_tokens: int = 4000) -> tuple[str, dict]:
        """One free-text call. Returns (text, usage)."""
        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
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


def ping() -> bool:
    """Validate the shared Nebius credentials without spending tokens."""
    get_client(Role.REASONER)._client.models.retrieve(cfg.reasoner_model)
    return True
