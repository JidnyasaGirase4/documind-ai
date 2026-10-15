"""Embedding providers behind one small interface so they can be swapped via configuration."""

import hashlib
import math
import re
from functools import lru_cache
from typing import Protocol

from app.core.config import settings

_BATCH_SIZE = 64


class EmbeddingError(Exception):
    """The embedding provider is missing, misconfigured or failed."""


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    """Real semantic embeddings. The model is downloaded on first use (needs internet once)."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                try:
                    # Use the local cache when the model is already downloaded: no network needed.
                    self._model = SentenceTransformer(self.model_name, local_files_only=True)
                except Exception:
                    self._model = SentenceTransformer(self.model_name)  # first run: download it
            except Exception as exc:
                raise EmbeddingError(f"The embedding model '{self.model_name}' could not be loaded: {exc}") from exc
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        try:
            out: list[list[float]] = []
            for i in range(0, len(texts), _BATCH_SIZE):
                vectors = model.encode(texts[i : i + _BATCH_SIZE], normalize_embeddings=True, show_progress_bar=False)
                out.extend(v.tolist() for v in vectors)
            return out
        except Exception as exc:
            raise EmbeddingError(f"Embedding failed: {exc}") from exc


class HashingEmbedder:
    """DEVELOPMENT/TEST ONLY. A deterministic bag-of-words hashing embedder with no model download.
    It matches shared words, not meaning, so it is much weaker than a real model."""

    DIM = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * self.DIM
        for token in re.findall(r"\w+", text.lower()):
            digest = hashlib.sha1(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.DIM
            vec[idx] += 1.0 if digest[4] % 2 == 0 else -1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


@lru_cache
def get_embedder() -> Embedder:
    provider = settings.embedding_provider.lower()
    if provider == "sentence_transformers":
        return SentenceTransformerEmbedder(settings.embedding_model)
    if provider == "hashing":
        return HashingEmbedder()
    raise EmbeddingError(f"Unknown EMBEDDING_PROVIDER '{settings.embedding_provider}'.")
