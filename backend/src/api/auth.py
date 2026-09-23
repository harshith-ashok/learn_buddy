from datetime import datetime, timezone

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.api.deps import CacheDep
from src.core.cache import CacheClient
from src.core.errors import ConflictError, UnauthorizedError
from src.core.security import (
    TokenPayload,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from src.db.models import Student
from src.db.session import DbSession

router = APIRouter(prefix="/auth", tags=["auth"])

_BLACKLIST_PREFIX = "revoked_refresh_jti"


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def _blacklist_key(jti: str) -> str:
    return f"{_BLACKLIST_PREFIX}:{jti}"


async def _revoke(cache: CacheClient, payload: TokenPayload) -> None:
    remaining_seconds = max(1, int((payload.exp - datetime.now(timezone.utc)).total_seconds()))
    await cache.set(_blacklist_key(payload.jti), "1", ttl_seconds=remaining_seconds)


def _issue_tokens(student_id: str) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(student_id), refresh_token=create_refresh_token(student_id)
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    existing = await db.scalar(select(Student).where(Student.email == payload.email))
    if existing is not None:
        raise ConflictError("Email already registered")

    student = Student(
        email=payload.email, hashed_password=hash_password(payload.password), full_name=payload.full_name
    )
    db.add(student)
    await db.commit()

    return _issue_tokens(str(student.id))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    student = await db.scalar(select(Student).where(Student.email == payload.email))
    if student is None or not verify_password(payload.password, student.hashed_password):
        raise UnauthorizedError("Invalid email or password")

    return _issue_tokens(str(student.id))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: DbSession, cache: CacheDep) -> TokenResponse:
    """Verify and consume a refresh token, issuing a fresh access/refresh pair.

    Rotation: the presented token's `jti` is blacklisted (TTL'd to its
    remaining validity) the moment it's used, so it can't be replayed even
    though it hasn't naturally expired yet.
    """
    token_payload = decode_token(payload.refresh_token, TokenType.REFRESH)
    if await cache.get(_blacklist_key(token_payload.jti)) is not None:
        raise UnauthorizedError("Refresh token has already been used")

    student = await db.scalar(select(Student).where(Student.id == token_payload.sub))
    if student is None:
        raise UnauthorizedError("Student not found")

    await _revoke(cache, token_payload)
    return _issue_tokens(str(student.id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, cache: CacheDep) -> None:
    """Revoke a refresh token early.

    Doesn't revoke the access token still live from the same session —
    access tokens aren't checked against the blacklist, only rotated on
    the next refresh. Full immediate revocation is a Phase 6 hardening
    item, not this phase's.
    """
    token_payload = decode_token(payload.refresh_token, TokenType.REFRESH)
    await _revoke(cache, token_payload)
