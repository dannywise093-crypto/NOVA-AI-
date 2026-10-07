from fastapi import Depends, Header, HTTPException

from app.auth.models import User
from app.auth.store import UserStore
from app.auth.tokens import verify_token
from app.core.config import settings

user_store = UserStore()


async def get_current_user(authorization: str | None = Header(default=None)) -> User:
    if not settings.auth_secret:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    user_id = verify_token(authorization[7:].strip(), settings.auth_secret)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = user_store.get(user_id)
    if user is None or user.disabled:
        raise HTTPException(status_code=401, detail="User not found")
    return user
