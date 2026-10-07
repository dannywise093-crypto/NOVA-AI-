from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import MemoryRow

def now():
    return datetime.now(timezone.utc)

async def create_memory(session: AsyncSession, owner_id: str, content: str, *, project_id: str | None = None, kind: str = "fact", importance: int = 50) -> MemoryRow:
    row = MemoryRow(id=f"mem_{uuid4().hex}", owner_id=owner_id, project_id=project_id,
        content=content.strip(), kind=kind, importance=max(0, min(100, importance)), created_at=now(), updated_at=now())
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row

async def search_memories(session: AsyncSession, owner_id: str, query: str, *, project_id: str | None = None, limit: int = 8) -> list[MemoryRow]:
    stmt = select(MemoryRow).where(MemoryRow.owner_id == owner_id)
    if project_id:
        stmt = stmt.where((MemoryRow.project_id == project_id) | (MemoryRow.project_id.is_(None)))
    else:
        stmt = stmt.where(MemoryRow.project_id.is_(None))
    rows = (await session.scalars(stmt)).all()
    terms = set(query.lower().split())
    return sorted(rows, key=lambda r: (len(terms & set(r.content.lower().split())), r.importance), reverse=True)[:limit]

async def delete_memory(session: AsyncSession, owner_id: str, memory_id: str) -> bool:
    row = await session.scalar(select(MemoryRow).where(MemoryRow.id == memory_id, MemoryRow.owner_id == owner_id))
    if row is None: return False
    await session.delete(row)
    await session.commit()
    return True
