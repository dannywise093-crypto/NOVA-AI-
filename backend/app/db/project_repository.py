from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ProjectRow
from app.projects.base import Project

def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)

def _project(row: ProjectRow) -> Project:
    return Project(id=row.id, name=row.name, description=row.description, owner_id=row.owner_id, created_at=row.created_at.isoformat(), updated_at=row.updated_at.isoformat())

async def create_project(session: AsyncSession, project: Project) -> Project:
    if await session.scalar(select(ProjectRow).where(ProjectRow.id == project.id)) is not None:
        raise ValueError(f"Project already exists: {project.id}")
    row = ProjectRow(id=project.id, owner_id=project.owner_id or "", name=project.name, description=project.description, created_at=_dt(project.created_at), updated_at=_dt(project.updated_at))
    session.add(row)
    await session.commit()
    return _project(row)

async def get_project(session: AsyncSession, project_id: str, owner_id: str) -> Project | None:
    row = await session.scalar(select(ProjectRow).where(ProjectRow.id == project_id, ProjectRow.owner_id == owner_id))
    return _project(row) if row else None

async def list_projects(session: AsyncSession, owner_id: str) -> list[Project]:
    rows = (await session.scalars(select(ProjectRow).where(ProjectRow.owner_id == owner_id).order_by(ProjectRow.created_at.desc()))).all()
    return [_project(row) for row in rows]
