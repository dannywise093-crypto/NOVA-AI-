from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.projects.base import Project
from app.projects.runtime import project_store

router = APIRouter(tags=["projects"])


class ProjectCreate(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str = ""

@router.post("/projects", response_model=Project)
async def create_project(request: ProjectCreate, user: User = Depends(get_current_user)) -> Project:
    try:
        return project_store.create(Project(id=request.id, name=request.name, description=request.description, owner_id=user.id))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.get("/projects", response_model=list[Project])
async def list_projects(user: User = Depends(get_current_user)) -> list[Project]:
    return [project for project in project_store.list() if project.owner_id == user.id]
