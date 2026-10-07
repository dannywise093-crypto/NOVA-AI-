from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db.project_repository import create_project, list_projects
from app.db.session import get_session
from app.projects.base import Project

router = APIRouter(tags=["projects"])

class ProjectCreate(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str = ""

@router.post("/projects", response_model=Project)
async def create_project_endpoint(request: ProjectCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> Project:
    try:
        return await create_project(session, Project(id=request.id, name=request.name, description=request.description, owner_id=user.id))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.get("/projects", response_model=list[Project])
async def list_project_endpoint(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> list[Project]:
    return await list_projects(session, user.id)
