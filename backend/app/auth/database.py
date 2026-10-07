from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import UserRow

async def load_user(session: AsyncSession, user_id: str) -> UserRow | None:
    return await session.scalar(select(UserRow).where(UserRow.id == user_id))
