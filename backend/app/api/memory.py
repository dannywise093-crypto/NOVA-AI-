from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db.memory_repository import create_memory, search_memories, delete_memory
from app.db.session import get_session

router = APIRouter(prefix="/memory", tags=["memory"])

class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    project_id: str | None = None
    kind: str = "fact"
    importance: int = Field(default=50, ge=0, le=100)

@router.post("")
async def add_memory(request: MemoryCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    row = await create_memory(session, user.id, request.content, project_id=request.project_id, kind=request.kind, importance=request.importance)
    return {"id": row.id, "content": row.content, "project_id": row.project_id, "kind": row.kind, "importance": row.importance}

@router.get("")
async def list_memory(query: str = "", project_id: str | None = None, limit: int = 20, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    rows = await search_memories(session, user.id, query, project_id=project_id, limit=min(limit, 50))
    return {"items": [{"id": r.id, "content": r.content, "project_id": r.project_id, "kind": r.kind, "importance": r.importance} for r in rows]}

@router.delete("/{memory_id}")
async def remove_memory(memory_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if not await delete_memory(session, user.id, memory_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True, "id": memory_id}
