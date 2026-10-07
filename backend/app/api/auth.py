from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.auth.models import User
from app.auth.security import hash_password, verify_password
from app.auth.store import UserStore
from app.auth.tokens import issue_token
from app.core.config import settings

router = APIRouter(tags=["auth"])
store = UserStore()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(RegisterRequest):
    pass


@router.post("/auth/register")
async def register(request: RegisterRequest) -> dict[str, str]:
    try:
        user = store.create(User(str(uuid4()), str(request.email), hash_password(request.password)))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"user_id": user.id, "email": user.email}


@router.post("/auth/login")
async def login(request: LoginRequest) -> dict[str, str]:
    user = store.get_by_email(str(request.email))
    if user is None or user.disabled or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not settings.auth_secret:
        raise HTTPException(status_code=503, detail="Authentication secret is not configured")
    return {"access_token": issue_token(user.id, settings.auth_secret), "token_type": "bearer"}
