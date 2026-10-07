"""Model-assisted query expansion with deterministic fallback."""

from __future__ import annotations

import json
from typing import Protocol

from app.knowledge.query_expansion import expand_query as deterministic_expand
from app.models.types import ChatMessage, ModelRequest


class QueryExpansionModel(Protocol):
    async def expand(self, query: str) -> list[str]: ...


class ModelQueryExpander:
    def __init__(self, provider, model: str) -> None:
        self.provider = provider
        self.model = model

    async def expand(self, query: str) -> list[str]:
        request = ModelRequest(messages=(
            ChatMessage(
                role="system",
                content=(
                    "Generate up to 4 concise search queries for retrieving evidence "
                    "from a private knowledge base. Preserve important names, versions, "
                    "technical terms, and constraints. Return ONLY a JSON array of strings."
                ),
            ),
            ChatMessage(role="user", content=query),
        ), temperature=0.0, max_tokens=256)
        response = await self.provider.chat(self.model, request)
        try:
            values = json.loads(response.content)
            if isinstance(values, list):
                result = [str(value).strip() for value in values if str(value).strip()]
                if result:
                    return result[:4]
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        return deterministic_expand(query, max_queries=4)


async def expand_with_model(query: str, provider=None, model: str = "") -> list[str]:
    if provider is None or not model:
        return deterministic_expand(query, max_queries=4)
    try:
        return await ModelQueryExpander(provider, model).expand(query)
    except Exception:
        return deterministic_expand(query, max_queries=4)
