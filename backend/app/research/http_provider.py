"""HTTP search provider for NOVA research."""

from __future__ import annotations

import httpx

from app.research.base import ResearchSource
from app.research.search import SearchProvider


class HttpSearchProvider(SearchProvider):
    def __init__(self, base_url: str, api_key: str, *, timeout: float = 12.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def search(self, query: str, *, limit: int = 8) -> list[ResearchSource]:
        if not self.base_url or not self.api_key:
            return []

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"query": query, "max_results": min(max(limit, 1), 20)}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/search", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        sources: list[ResearchSource] = []
        for item in data.get("results", []):
            uri = str(item.get("url") or item.get("uri") or "").strip()
            title = str(item.get("title") or "").strip()
            if not uri or not title:
                continue
            sources.append(ResearchSource(
                title=title,
                uri=uri,
                snippet=str(item.get("snippet") or item.get("description") or ""),
                publisher=item.get("publisher"),
                published_at=item.get("published_at"),
            ))
        return sources
