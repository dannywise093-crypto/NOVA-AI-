from app.artifacts.base import ProjectArtifact


class ArtifactStore:
    def __init__(self) -> None:
        self._items: dict[str, ProjectArtifact] = {}

    def create(self, artifact: ProjectArtifact) -> ProjectArtifact:
        if artifact.id in self._items:
            raise ValueError(f"Artifact already exists: {artifact.id}")
        self._items[artifact.id] = artifact
        return artifact

    def get(self, artifact_id: str) -> ProjectArtifact | None:
        return self._items.get(artifact_id)

    def list(self, project_id: str | None = None) -> list[ProjectArtifact]:
        items = list(self._items.values())
        return [item for item in items if project_id is None or item.project_id == project_id]
