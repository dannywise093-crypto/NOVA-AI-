"""NOVA memory formation and retrieval policy."""

from dataclasses import dataclass
import re
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.memory_repository import create_memory, search_memories


@dataclass(frozen=True)
class MemoryCandidate:
    content: str
    kind: str = "fact"
    importance: int = 50


class MemoryEngine:
    """Conservative memory layer.

    Automatic extraction is deliberately heuristic until NOVA has a dedicated
    memory model. It stores explicit preference/fact statements and avoids
    persisting secrets or obviously transient requests.
    """

    _patterns = (
        (re.compile(r"\bmy name is\s+([^.!?\n]+)", re.I), "identity", 85),
        (re.compile(r"\bcall me\s+([^.!?\n]+)", re.I), "preference", 75),
        (re.compile(r"\bi (?:prefer|like|love)\s+([^.!?\n]+)", re.I), "preference", 70),
        (re.compile(r"\bi (?:use|work with)\s+([^.!?\n]+)", re.I), "preference", 60),
        (re.compile(r"\bmy goal is\s+([^.!?\n]+)", re.I), "goal", 80),
    )

    _secret_terms = ("password", "passcode", "private key", "seed phrase", "api key", "secret")

    def extract(self, text: str) -> list[MemoryCandidate]:
        lowered = text.lower()
        if any(term in lowered for term in self._secret_terms):
            return []
        candidates: list[MemoryCandidate] = []
        for pattern, kind, importance in self._patterns:
            for match in pattern.finditer(text):
                value = match.group(1).strip()
                if 2 <= len(value) <= 300:
                    candidates.append(MemoryCandidate(
                        content=f"{kind}: {value}",
                        kind=kind,
                        importance=importance,
                    ))
        return candidates

    async def remember(self, session: AsyncSession, owner_id: str, text: str, *, project_id: str | None = None) -> list:
        candidates = self.extract(text)
        saved = []
        for candidate in candidates:
            existing = await search_memories(
                session, owner_id, candidate.content, project_id=project_id, limit=5
            )
            if any(self._similar(candidate.content, row.content) for row in existing):
                continue
            saved.append(await create_memory(
                session, owner_id, candidate.content,
                project_id=project_id,
                kind=candidate.kind,
                importance=candidate.importance,
            ))
        return saved

    @staticmethod
    def _similar(left: str, right: str) -> bool:
        a = set(re.findall(r"\w+", left.lower()))
        b = set(re.findall(r"\w+", right.lower()))
        return bool(a and b and len(a & b) / max(len(a), len(b)) >= 0.75)
