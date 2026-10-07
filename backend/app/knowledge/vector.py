from abc import ABC, abstractmethod

from app.knowledge.ingest import DocumentChunk


class VectorStore(ABC):
    @abstractmethod
    async def upsert(self, chunks: list[DocumentChunk]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def search(self, query: str, *, limit: int = 8) -> list[DocumentChunk]:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._chunks: list[DocumentChunk] = []

    async def upsert(self, chunks: list[DocumentChunk]) -> None:
        self._chunks.extend(chunks)

    async def search(self, query: str, *, limit: int = 8) -> list[DocumentChunk]:
        terms = set(query.lower().split())
        ranked = sorted(self._chunks, key=lambda c: len(terms & set(c.text.lower().split())), reverse=True)
        return ranked[:limit]
