"""CPU-local embeddings, no third-party billing — an emergency fallback
for Role.EMBEDDER when the configured provider (Nebius) is unreachable or
out of budget. Same "local classifier via transformers" pattern this app
already uses for the Checker (app/reasoning/checker.py's HHEM), not a new
kind of dependency: the `transformers`/`torch` packages are already
required for that.

sentence-transformers/all-MiniLM-L6-v2 (22M params, 384-dim) — small
enough to download and run on this box's CPU in seconds, not Qwen3-
Embedding-8B's output space, so switching to this requires re-embedding
every already-stored chunk and recreating the vector index at the new
dimension (see the one-off backfill run alongside this fix, not part of
normal app boot).
"""
from __future__ import annotations

import torch
from transformers import AutoModel, AutoTokenizer

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DIMENSIONS = 384

_tokenizer = None
_model = None


def _load():
    global _tokenizer, _model
    if _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
        _model = AutoModel.from_pretrained(_MODEL_NAME)
        _model.eval()
    return _tokenizer, _model


class LocalEmbedderClient:
    role = None
    model = _MODEL_NAME

    def ping(self) -> None:
        """No credentials to validate (CPU-local, no API key) — just
        confirms the model actually loads, the equivalent failure mode
        a real provider's ping() would catch."""
        _load()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        tokenizer, model = _load()
        encoded = tokenizer(texts, padding=True, truncation=True, max_length=512,
                            return_tensors="pt")
        with torch.no_grad():
            output = model(**encoded)
        # Mean-pool token embeddings over real (non-padding) tokens, then
        # L2-normalize so cosine similarity (the Neo4j vector index's
        # configured metric) behaves the same way it would for a model
        # that normalizes natively.
        mask = encoded["attention_mask"].unsqueeze(-1).float()
        summed = (output.last_hidden_state * mask).sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1e-9)
        pooled = summed / counts
        normalized = torch.nn.functional.normalize(pooled, p=2, dim=1)
        return normalized.tolist()
