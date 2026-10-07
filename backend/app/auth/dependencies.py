from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.database import load_user
from app.auth.models import User
from app.auth.tokens import verify_token
from app.core.config import settings
from app.db.session import get_session

async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not settings.auth_secret:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    user_id = verify_token(authorization[7:].strip(), settings.auth_secret)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    row = await load_user(session, user_id)
    if row is None or row.disabled:
        raise HTTPException(status_code=401, detail="User not found")
    return User(row.id, row.email, "", row.created_at.isoformat(), row.disabled)
