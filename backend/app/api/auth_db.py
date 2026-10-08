from datetime import datetime, timezone
import asyncio
from urllib.parse import urlencode
from uuid import uuid4
import base64
import hashlib
import hmac
import json
import secrets
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password, verify_password
from app.auth.tokens import issue_token
from app.core.config import settings
from app.db.models import UserRow
from app.db.session import get_session
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

router = APIRouter(tags=["auth"])

_PENDING_CODES: dict[str, tuple[str, float]] = {}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(RegisterRequest):
    pass


class OAuthExchangeRequest(BaseModel):
    code: str = Field(min_length=20, max_length=256)


class GoogleMobileRequest(BaseModel):
    id_token: str = Field(min_length=100, max_length=12000)


def _require_oauth(provider: str) -> str:
    base = settings.oauth_public_base_url.strip().rstrip("/")
    if not base:
        raise HTTPException(status_code=503, detail="OAuth public URL is not configured")
    if provider == "google" and not settings.google_oauth_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    if provider == "x" and not settings.x_oauth_client_id:
        raise HTTPException(status_code=503, detail="X OAuth is not configured")
    return base


def _sign_state(payload: dict[str, object]) -> str:
    raw = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    sig = hmac.new(settings.auth_secret.encode(), raw.encode(), hashlib.sha256).digest()
    return raw + "." + base64.urlsafe_b64encode(sig).rstrip(b"=").decode()


def _read_state(value: str) -> dict[str, object]:
    raw, sig = value.split(".", 1)
    expected = hmac.new(settings.auth_secret.encode(), raw.encode(), hashlib.sha256).digest()
    actual = base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))
    if not hmac.compare_digest(actual, expected):
        raise ValueError("invalid state")
    data = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
    if int(data["exp"]) < int(time.time()):
        raise ValueError("expired state")
    return data


def _pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()


@router.post("/auth/register")
async def register(request: RegisterRequest, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    email = str(request.email).lower()
    if await session.scalar(select(UserRow).where(UserRow.email == email)) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = UserRow(
        id=str(uuid4()),
        email=email,
        password_hash=hash_password(request.password),
        created_at=datetime.now(timezone.utc),
        disabled=False,
    )
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


@router.get("/auth/google/config")
async def google_config() -> dict[str, str]:
    if not settings.google_oauth_client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    return {"client_id": settings.google_oauth_client_id}


@router.post("/auth/google/mobile")
async def google_mobile_login(
    request: GoogleMobileRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if not settings.google_oauth_client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    if not settings.auth_secret:
        raise HTTPException(status_code=503, detail="Authentication secret is not configured")

    try:
        info = await asyncio.to_thread(
            google_id_token.verify_oauth2_token,
            request.id_token,
            google_requests.Request(),
            settings.google_oauth_client_id,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google identity token")

    issuer = str(info.get("iss") or "")
    if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=401, detail="Invalid Google token issuer")
    if not info.get("email_verified"):
        raise HTTPException(status_code=403, detail="Google email is not verified")

    subject = str(info.get("sub") or "")
    email = str(info.get("email") or "").lower()
    if not subject or not email:
        raise HTTPException(status_code=401, detail="Google account identity is incomplete")

    user = await session.scalar(select(UserRow).where(UserRow.email == email))
    if user is None:
        user = UserRow(
            id=str(uuid4()),
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            created_at=datetime.now(timezone.utc),
            disabled=False,
        )
        session.add(user)
        await session.commit()
    if user.disabled:
        raise HTTPException(status_code=403, detail="NOVA account is disabled")

    return {
        "access_token": issue_token(user.id, settings.auth_secret),
        "token_type": "bearer",
    }


@router.get("/auth/{provider}/start")
async def oauth_start(provider: str) -> RedirectResponse:
    provider = provider.lower()
    if provider not in {"google", "x"}:
        raise HTTPException(status_code=404, detail="Unsupported OAuth provider")
    base = _require_oauth(provider)
    if not settings.auth_secret:
        raise HTTPException(status_code=503, detail="Authentication secret is not configured")

    verifier = secrets.token_urlsafe(48)
    state = _sign_state({
        "provider": provider,
        "verifier": verifier,
        "exp": int(time.time()) + 600,
        "nonce": secrets.token_urlsafe(24),
    })
    redirect_uri = f"{base}/api/auth/{provider}/callback"

    if provider == "google":
        params = {
            "client_id": settings.google_oauth_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": _pkce_challenge(verifier),
            "code_challenge_method": "S256",
            "access_type": "offline",
        }
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    else:
        params = {
            "response_type": "code",
            "client_id": settings.x_oauth_client_id,
            "redirect_uri": redirect_uri,
            "scope": "users.read tweet.read offline.access",
            "state": state,
            "code_challenge": _pkce_challenge(verifier),
            "code_challenge_method": "S256",
        }
        url = "https://x.com/i/oauth2/authorize?" + urlencode(params)

    return RedirectResponse(url, status_code=302)


async def _exchange_provider_code(provider: str, code: str, state: dict[str, object]) -> tuple[str, str]:
    base = settings.oauth_public_base_url.strip().rstrip("/")
    redirect_uri = f"{base}/api/auth/{provider}/callback"
    verifier = str(state["verifier"])

    async with httpx.AsyncClient(timeout=15) as client:
        if provider == "google":
            token_data = {
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            }
            token_response = await client.post("https://oauth2.googleapis.com/token", data=token_data)
            if token_response.status_code >= 400:
                raise HTTPException(status_code=502, detail="Google token exchange failed")
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise HTTPException(status_code=502, detail="Google did not return an access token")
            profile_response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if profile_response.status_code >= 400:
                raise HTTPException(status_code=502, detail="Google profile lookup failed")
            profile = profile_response.json()
            subject = str(profile.get("sub") or "")
            email = str(profile.get("email") or "").lower()
            if not subject or not email:
                raise HTTPException(status_code=502, detail="Google account did not provide an email")
            return subject, email

        token_data = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": settings.x_oauth_client_id,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        }
        if settings.x_oauth_client_secret:
            token_data["client_secret"] = settings.x_oauth_client_secret
        token_response = await client.post(
            "https://api.x.com/2/oauth2/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_response.status_code >= 400:
            raise HTTPException(status_code=502, detail="X token exchange failed")
        access_token = token_response.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=502, detail="X did not return an access token")
        profile_response = await client.get(
            "https://api.x.com/2/users/me",
            params={"user.fields": "id,username"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if profile_response.status_code >= 400:
            raise HTTPException(status_code=502, detail="X profile lookup failed")
        profile = profile_response.json().get("data") or {}
        subject = str(profile.get("id") or "")
        username = str(profile.get("username") or "")
        if not subject:
            raise HTTPException(status_code=502, detail="X account identity was not returned")
        # X may not return an email address; use a stable internal identity address.
        return subject, f"x_{subject}@accounts.nova.local"


@router.get("/auth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    provider = provider.lower()
    if provider not in {"google", "x"}:
        raise HTTPException(status_code=404, detail="Unsupported OAuth provider")
    try:
        state_data = _read_state(state)
        if state_data.get("provider") != provider:
            raise ValueError("provider mismatch")
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, base64.binascii.Error):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    subject, email = await _exchange_provider_code(provider, code, state_data)
    identity_key = f"{provider}:{subject}"
    # Keep the provider identity in the in-memory code until the app exchanges it.
    # The NOVA user itself is persisted in the normal users table.
    user = await session.scalar(select(UserRow).where(UserRow.email == email))
    if user is None:
        user = UserRow(
            id=str(uuid4()),
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            created_at=datetime.now(timezone.utc),
            disabled=False,
        )
        session.add(user)
        await session.commit()
    if user.disabled:
        raise HTTPException(status_code=403, detail="NOVA account is disabled")

    one_time_code = secrets.token_urlsafe(32)
    _PENDING_CODES[one_time_code] = (user.id, time.time() + 120)
    # identity_key is deliberately not returned to the app; it is only part of server-side flow logging/debugging.
    _ = identity_key
    return RedirectResponse(
        f"nova://auth/callback?code={one_time_code}",
        status_code=302,
    )


@router.post("/auth/oauth/exchange")
async def oauth_exchange(
    request: OAuthExchangeRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    record = _PENDING_CODES.pop(request.code, None)
    if record is None or record[1] < time.time():
        raise HTTPException(status_code=401, detail="OAuth code expired")
    user = await session.get(UserRow, record[0])
    if user is None or user.disabled:
        raise HTTPException(status_code=401, detail="OAuth account unavailable")
    if not settings.auth_secret:
        raise HTTPException(status_code=503, detail="Authentication secret is not configured")
    return {"access_token": issue_token(user.id, settings.auth_secret), "token_type": "bearer"}
