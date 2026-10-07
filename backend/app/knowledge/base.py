from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class KnowledgeSource:
    id: str
    title: str
    uri: str | None = None
    source_type: str = "document"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeItem:
    id: str
    text: str
    source: KnowledgeSource
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
