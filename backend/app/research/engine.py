"""Research orchestration helpers."""

from dataclasses import dataclass

from app.research.base import ResearchSource
from app.research.search import SearchProvider
from app.research.reader import Evidence, SourceReader


@dataclass(frozen=True)
class ResearchBundle:
    query: str
    sources: tuple[ResearchSource, ...]
    evidence: tuple[Evidence, ...] = ()


class ResearchEngine:
    def __init__(self, provider: SearchProvider) -> None:
        self.provider = provider
        self.reader = reader or SourceReader()

    async def gather(self, query: str, *, rounds: int = 2, limit_per_round: int = 6) -> ResearchBundle:
        """Gather multiple result sets while deduplicating URLs."""
        queries = [query]
        if rounds > 1:
            queries.append(f"{query} official documentation primary source")

        seen: set[str] = set()
        sources: list[ResearchSource] = []
        for variant in queries[:max(1, min(rounds, 3))]:
            for source in await self.provider.search(variant, limit=limit_per_round):
                if source.uri in seen:
                    continue
                seen.add(source.uri)
                sources.append(source)
        evidence: list[Evidence] = []
        for source in sources[:12]:
            item = await self.reader.read(source.uri, title=source.title)
            if item is not None:
                evidence.append(item)
        return ResearchBundle(query=query, sources=tuple(sources), evidence=tuple(evidence))
