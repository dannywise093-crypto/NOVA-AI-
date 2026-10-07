from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.projects.base import Project
from app.projects.store import InMemoryProjectStore

router = APIRouter(tags=["projects"])
store = InMemoryProjectStore()


class ProjectCreate(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


@router.post("/projects", response_model=Project)
async def create_project(request: ProjectCreate) -> Project:
    try:
        return store.create(Project(id=request.id, name=request.name, description=request.description))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/projects", response_model=list[Project])
async def list_projects() -> list[Project]:
    return store.list()
