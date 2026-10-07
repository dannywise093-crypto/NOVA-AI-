from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.artifacts.base import ProjectArtifact
from app.db.models import ArtifactRow

def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)

def _artifact(row: ArtifactRow) -> ProjectArtifact:
    return ProjectArtifact(id=row.id, project_id=row.project_id, name=row.name, mime_type=row.mime_type, size_bytes=row.size_bytes, storage_key=row.storage_key, created_at=row.created_at.isoformat())

async def create_artifact(session: AsyncSession, artifact: ProjectArtifact) -> ProjectArtifact:
    row = ArtifactRow(id=artifact.id, project_id=artifact.project_id, name=artifact.name, mime_type=artifact.mime_type, size_bytes=artifact.size_bytes, storage_key=artifact.storage_key, created_at=_dt(artifact.created_at))
    session.add(row)
    await session.commit()
    return _artifact(row)

async def list_artifacts(session: AsyncSession, project_ids: set[str]) -> list[ProjectArtifact]:
    if not project_ids:
        return []
    rows = (await session.scalars(select(ArtifactRow).where(ArtifactRow.project_id.in_(project_ids)).order_by(ArtifactRow.created_at.desc()))).all()
    return [_artifact(row) for row in rows]
