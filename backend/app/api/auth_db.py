from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.security import hash_password, verify_password
from app.auth.tokens import issue_token
from app.core.config import settings
from app.db.models import UserRow
from app.db.session import get_session

router = APIRouter(tags=["auth"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)

class LoginRequest(RegisterRequest):
    pass

@router.post("/auth/register")
async def register(request: RegisterRequest, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    email = str(request.email).lower()
    if await session.scalar(select(UserRow).where(UserRow.email == email)) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = UserRow(id=str(uuid4()), email=email, password_hash=hash_password(request.password), created_at=datetime.now(timezone.utc), disabled=False)
    session.add(user)
    await session.commit()
    return {"user_id": user.id, "email": user.email}

@router.post("/auth/login")
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    user = await session.scalar(select(UserRow).where(UserRow.email == str(request.email).lower()))
    if user is None or user.disabled or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not settings.auth_secret:
        raise HTTPException(status_code=503, detail="Authentication secret is not configured")
    return {"access_token": issue_token(user.id, settings.auth_secret), "token_type": "bearer"}
