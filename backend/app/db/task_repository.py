"""Persistent agent task records."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.db.models import Base
from sqlalchemy.orm import Mapped, mapped_column


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentTaskRow(Base):
    __tablename__ = "agent_tasks"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), nullable=True, index=True)
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


async def create_task(session: AsyncSession, task: AgentTaskRow) -> AgentTaskRow:
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def get_task(session: AsyncSession, task_id: str, owner_id: str) -> AgentTaskRow | None:
    return await session.scalar(select(AgentTaskRow).where(
        AgentTaskRow.id == task_id, AgentTaskRow.owner_id == owner_id
    ))


async def update_task(session: AsyncSession, task: AgentTaskRow, *, status: str | None = None,
                      progress: int | None = None, result: str | None = None,
                      error: str | None = None) -> AgentTaskRow:
    if status is not None:
        task.status = status
    if progress is not None:
        task.progress = max(0, min(100, progress))
    if result is not None:
        task.result = result
    if error is not None:
        task.error = error
    task.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(task)
    return task


async def recoverable_tasks(session: AsyncSession, limit: int = 20) -> list[AgentTaskRow]:
    now = datetime.now(timezone.utc)
    return list((await session.scalars(
        select(AgentTaskRow)
        .where(or_(
            AgentTaskRow.status == TaskStatus.QUEUED,
            (AgentTaskRow.status == TaskStatus.RUNNING) & (AgentTaskRow.lease_until != None) & (AgentTaskRow.lease_until < now),
        ))
        .order_by(AgentTaskRow.created_at)
        .limit(limit)
    )).all())


async def claim_task(session: AsyncSession, task_id: str, lease_seconds: int = 60) -> AgentTaskRow | None:
    task = await session.scalar(select(AgentTaskRow).where(AgentTaskRow.id == task_id))
    if task is None:
        return None
    now = datetime.now(timezone.utc)
    if task.status not in {TaskStatus.QUEUED, TaskStatus.RUNNING}:
        return None
    if task.status == TaskStatus.RUNNING and task.lease_until and task.lease_until >= now:
        return None
    task.status = TaskStatus.RUNNING
    task.attempts += 1
    task.lease_until = now + __import__("datetime").timedelta(seconds=lease_seconds)
    task.updated_at = now
    await session.commit()
    await session.refresh(task)
    return task
