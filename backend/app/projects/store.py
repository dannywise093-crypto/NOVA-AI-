from app.projects.base import Project


class InMemoryProjectStore:
    """Development store; replace with PostgreSQL-backed persistence."""

    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}

    def create(self, project: Project) -> Project:
        if project.id in self._projects:
            raise ValueError(f"Project already exists: {project.id}")
        self._projects[project.id] = project
        return project

    def get(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def list(self) -> list[Project]:
        return list(self._projects.values())
