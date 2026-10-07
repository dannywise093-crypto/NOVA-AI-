from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.conversations.base import Conversation, Message
from app.db.models import ConversationRow, MessageRow

def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)

def _conversation(row: ConversationRow) -> Conversation:
    return Conversation(
        id=row.id, title=row.title, project_id=row.project_id, owner_id=row.owner_id,
        messages=[Message(id=m.id, role=m.role, content=m.content, created_at=m.created_at.isoformat()) for m in row.messages],
        created_at=row.created_at.isoformat(), updated_at=row.updated_at.isoformat(),
    )

async def create_conversation(session: AsyncSession, item: Conversation) -> Conversation:
    if await session.scalar(select(ConversationRow).where(ConversationRow.id == item.id)) is not None:
        raise ValueError(f"Conversation already exists: {item.id}")
    row = ConversationRow(id=item.id, owner_id=item.owner_id or "", project_id=item.project_id, title=item.title,
        created_at=_dt(item.created_at), updated_at=_dt(item.updated_at))
    session.add(row)
    await session.commit()
    return _conversation(row)

async def get_conversation(session: AsyncSession, conversation_id: str, owner_id: str) -> Conversation | None:
    row = await session.scalar(select(ConversationRow).options(selectinload(ConversationRow.messages)).where(ConversationRow.id == conversation_id, ConversationRow.owner_id == owner_id))
    return _conversation(row) if row else None

async def list_conversations(session: AsyncSession, owner_id: str, project_id: str | None = None) -> list[Conversation]:
    query = select(ConversationRow).options(selectinload(ConversationRow.messages)).where(ConversationRow.owner_id == owner_id)
    if project_id is not None:
        query = query.where(ConversationRow.project_id == project_id)
    rows = (await session.scalars(query.order_by(ConversationRow.updated_at.desc()))).unique().all()
    return [_conversation(row) for row in rows]

async def save_conversation(session: AsyncSession, item: Conversation) -> Conversation:
    row = await session.scalar(select(ConversationRow).options(selectinload(ConversationRow.messages)).where(ConversationRow.id == item.id, ConversationRow.owner_id == item.owner_id))
    if row is None:
        raise ValueError("Conversation does not exist")
    row.title, row.updated_at = item.title, _dt(item.updated_at)
    row.messages.clear()
    row.messages.extend(MessageRow(id=m.id, conversation_id=item.id, role=m.role, content=m.content, created_at=_dt(m.created_at)) for m in item.messages)
    await session.commit()
    return _conversation(row)
