"""Database-backed recovery worker for persistent agent tasks."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timezone

from app.core.container import build_orchestrator
from app.db.session import SessionFactory
from app.db.task_repository import TaskStatus, claim_task, recoverable_tasks, update_task, heartbeat_task
from app.models.types import ChatMessage


class DurableTaskWorker:
    def __init__(self, poll_seconds: float = 2.0, concurrency: int = 2, lease_seconds: int = 60) -> None:
        self.poll_seconds = max(0.5, poll_seconds)
        self.concurrency = max(1, concurrency)
        self.lease_seconds = max(15, lease_seconds)
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._running: set[str] = set()

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._loop(), name="nova-durable-task-worker")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                async with SessionFactory() as session:
                    candidates = await recoverable_tasks(session, limit=self.concurrency * 2)
                for candidate in candidates:
                    if len(self._running) >= self.concurrency or candidate.id in self._running:
                        continue
                    self._running.add(candidate.id)
                    asyncio.create_task(self._run(candidate.id), name=f"nova-task-{candidate.id}")
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.poll_seconds)
            except asyncio.TimeoutError:
                pass

    async def _run(self, task_id: str) -> None:
        try:
            async with SessionFactory() as session:
                task = await claim_task(session, task_id, self.lease_seconds)
                if task is None:
                    return
                goal = task.goal
                await update_task(session, task, progress=max(task.progress, 10))

            async with SessionFactory() as session:
                task = await session.get(
                    __import__("app.db.task_repository", fromlist=["AgentTaskRow"]).AgentTaskRow,
                    task_id,
                )
                if task is None or task.status == TaskStatus.CANCELLED:
                    return
                orchestrator = build_orchestrator(session)
                heartbeat = asyncio.create_task(self._heartbeat(task_id), name=f"nova-heartbeat-{task_id}")
                try:
                    result = await orchestrator.run(goal, [ChatMessage(role="user", content=goal)])
                finally:
                    heartbeat.cancel()
                    with suppress(asyncio.CancelledError):
                        await heartbeat
                await update_task(
                    session, task, status=TaskStatus.COMPLETED,
                    progress=100, result=result.response.content,
                )
                task.lease_until = None
                await session.commit()
        except Exception as exc:
            async with SessionFactory() as session:
                task = await session.get(
                    __import__("app.db.task_repository", fromlist=["AgentTaskRow"]).AgentTaskRow,
                    task_id,
                )
                if task is not None and task.status != TaskStatus.CANCELLED:
                    task.status = TaskStatus.QUEUED if task.attempts < 3 else TaskStatus.FAILED
                    task.error = str(exc)[:4000]
                    task.lease_until = None
                    task.updated_at = datetime.now(timezone.utc)
                    await session.commit()
        finally:
            self._running.discard(task_id)

    async def _heartbeat(self, task_id: str) -> None:
        interval = max(5.0, self.lease_seconds / 3)
        while True:
            await asyncio.sleep(interval)
            async with SessionFactory() as session:
                if not await heartbeat_task(session, task_id, self.lease_seconds):
                    return


durable_task_worker = DurableTaskWorker()
