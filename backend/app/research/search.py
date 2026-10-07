from abc import ABC, abstractmethod

from app.research.base import ResearchSource


class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, *, limit: int = 8) -> list[ResearchSource]:
        raise NotImplementedError


class UnconfiguredSearchProvider(SearchProvider):
    async def search(self, query: str, *, limit: int = 8) -> list[ResearchSource]:
        return []
