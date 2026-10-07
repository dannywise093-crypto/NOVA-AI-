"""Embedding interfaces and a deterministic fallback encoder."""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class HashEmbeddingProvider(EmbeddingProvider):
    """Offline fallback; replace with a real embedding model in production."""

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = text.lower().split()
        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """Embedding provider for OpenAI-compatible /embeddings APIs."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def embed(self, text: str) -> list[float]:
        import httpx
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "input": text},
            )
            response.raise_for_status()
            data = response.json()
        embedding = data.get("data", [{}])[0].get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise ValueError("Embedding provider returned no vector")
        return [float(value) for value in embedding]


def build_embedding_provider(base_url: str, api_key: str, model: str) -> EmbeddingProvider:
    if api_key and model:
        return OpenAICompatibleEmbeddingProvider(base_url, api_key, model)
    return HashEmbeddingProvider()
