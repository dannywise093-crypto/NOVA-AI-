from abc import ABC, abstractmethod
from pathlib import Path
from app.core.config import settings

class ArtifactStorage(ABC):
    @abstractmethod
    async def put(self, key: str, data: bytes) -> str: ...
    @abstractmethod
    async def get(self, key: str) -> bytes: ...

class LocalArtifactStorage(ArtifactStorage):
    def __init__(self, root: str = "./data/artifacts") -> None:
        self.root = Path(root)
    def _path(self, key: str) -> Path:
        safe = key.removeprefix("local://").lstrip("/").replace("..", "__")
        return self.root / safe
    async def put(self, key: str, data: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"local://{path.relative_to(self.root)}"
    async def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

def build_artifact_storage() -> ArtifactStorage:
    return LocalArtifactStorage()
