from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Artifact:
    id: str
    name: str
    kind: str
    uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Project:
    id: str
    name: str
    description: str = ""
    artifact_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def touch(self) -> None:
        self.updated_at = now_iso()
