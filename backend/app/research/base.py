from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResearchSource:
    title: str
    uri: str
    snippet: str = ""
    publisher: str | None = None
    published_at: str | None = None


@dataclass(frozen=True)
class ResearchResult:
    query: str
    answer: str
    sources: tuple[ResearchSource, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
