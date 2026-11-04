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
        # Batched, not one forward pass over the whole document — found
        # live, 2026-11-04: a single large book's passage list (671 pages,
        # thousands of passages) ran through tokenizer(texts, padding=
        # True, ...) + model(**encoded) as ONE batch. padding=True pads
        # every sequence to the longest in the batch (up to 512 tokens),
        # so activation memory for that single forward pass scales with
        # batch_size * seq_len — for a batch in the thousands, that's
        # gigabytes held at once on CPU, independent of anything else in
        # the ingest pipeline (this call is synchronous, unaffected by
        # app/ingestion/queue.py's own concurrency cap or the KG-
        # extraction ThreadPoolExecutor's worker count). This was the
        # actual OOM driver DEPLOY.md's MemoryMax raises kept working
        # around rather than fixing. A fixed batch size keeps peak memory
        # roughly constant regardless of how many passages a document has.
        _BATCH = 32
        out: list[list[float]] = []
        for i in range(0, len(texts), _BATCH):
            batch = texts[i:i + _BATCH]
            encoded = tokenizer(batch, padding=True, truncation=True, max_length=512,
                                return_tensors="pt")
            with torch.no_grad():
                output = model(**encoded)
            # Mean-pool token embeddings over real (non-padding) tokens,
            # then L2-normalize so cosine similarity (the Neo4j vector
            # index's configured metric) behaves the same way it would
            # for a model that normalizes natively.
            mask = encoded["attention_mask"].unsqueeze(-1).float()
            summed = (output.last_hidden_state * mask).sum(dim=1)
            counts = mask.sum(dim=1).clamp(min=1e-9)
            pooled = summed / counts
            normalized = torch.nn.functional.normalize(pooled, p=2, dim=1)
            out.extend(normalized.tolist())
        return out
