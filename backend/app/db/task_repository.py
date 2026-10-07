"""Persistent agent task records."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from enum import StrEnum
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, update
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
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    now = datetime.now(timezone.utc)
    lease_until = now + timedelta(seconds=lease_seconds)
    result = await session.execute(
        update(AgentTaskRow)
        .where(
            AgentTaskRow.id == task_id,
            or_(
                AgentTaskRow.status == TaskStatus.QUEUED,
                (AgentTaskRow.status == TaskStatus.RUNNING)
                & (AgentTaskRow.lease_until != None)
                & (AgentTaskRow.lease_until < now),
            ),
        )
        .values(
            status=TaskStatus.RUNNING,
            attempts=AgentTaskRow.attempts + 1,
            lease_until=lease_until,
            heartbeat_at=now,
            updated_at=now,
        )
    )
    if result.rowcount != 1:
        await session.rollback()
        return None
    await session.commit()
    return await session.scalar(select(AgentTaskRow).where(AgentTaskRow.id == task_id))


async def heartbeat_task(session: AsyncSession, task_id: str, lease_seconds: int = 60) -> bool:
    # heartbeat_at is the immutable claim token. A stale worker therefore
    # cannot accidentally renew or complete a task after it is reclaimed.
    task = await session.scalar(select(AgentTaskRow).where(
        AgentTaskRow.id == task_id, AgentTaskRow.status == TaskStatus.RUNNING
    ))
    if task is None:
        return False
    now = datetime.now(timezone.utc)
    task.lease_until = now + timedelta(seconds=lease_seconds)
    task.updated_at = now
    await session.commit()
    return True


async def complete_task(
    session: AsyncSession,
    task_id: str,
    claim_token: datetime,
    *,
    result: str,
) -> bool:
    now = datetime.now(timezone.utc)
    updated = await session.execute(
        update(AgentTaskRow)
        .where(
            AgentTaskRow.id == task_id,
            AgentTaskRow.status == TaskStatus.RUNNING,
            AgentTaskRow.heartbeat_at == claim_token,
        )
        .values(
            status=TaskStatus.COMPLETED,
            progress=100,
            result=result,
            lease_until=None,
            updated_at=now,
        )
    )
    await session.commit()
    return updated.rowcount == 1
