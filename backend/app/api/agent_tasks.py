"""Agent task API for persistent task lifecycle."""

from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db.session import get_session
from app.db.task_repository import AgentTaskRow, TaskStatus, create_task, get_task, update_task

router = APIRouter(tags=["agent-tasks"])


class AgentTaskCreate(BaseModel):
    goal: str = Field(min_length=1, max_length=20000)
    conversation_id: str | None = None


class AgentTaskView(BaseModel):
    id: str
    goal: str
    status: str
    progress: int
    result: str | None
    error: str | None


def view(task: AgentTaskRow) -> AgentTaskView:
    return AgentTaskView(id=task.id, goal=task.goal, status=task.status,
                         progress=task.progress, result=task.result, error=task.error)


@router.post("/agent-tasks", response_model=AgentTaskView)
async def create_agent_task(request: AgentTaskCreate, user: User = Depends(get_current_user),
                            session: AsyncSession = Depends(get_session)) -> AgentTaskView:
    now = datetime.now(timezone.utc)
    task = AgentTaskRow(
        id=str(uuid4()), owner_id=user.id, conversation_id=request.conversation_id,
        goal=request.goal, status=TaskStatus.QUEUED, progress=0,
        created_at=now, updated_at=now,
    )
    created = await create_task(session, task)
    return view(created)


@router.get("/agent-tasks/{task_id}", response_model=AgentTaskView)
async def get_agent_task(task_id: str, user: User = Depends(get_current_user),
                         session: AsyncSession = Depends(get_session)) -> AgentTaskView:
    task = await get_task(session, task_id, user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Agent task not found")
    return view(task)


@router.post("/agent-tasks/{task_id}/cancel", response_model=AgentTaskView)
async def cancel_agent_task(task_id: str, user: User = Depends(get_current_user),
                            session: AsyncSession = Depends(get_session)) -> AgentTaskView:
    task = await get_task(session, task_id, user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Agent task not found")
    if task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
        return view(task)
    return view(await update_task(session, task, status=TaskStatus.CANCELLED))
