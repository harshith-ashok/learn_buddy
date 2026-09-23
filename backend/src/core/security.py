import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum as PyEnum
from typing import Annotated, Any

import bcrypt
import jwt
from fastapi import Depends
from pydantic import BaseModel

from src.core.config import Settings, get_settings
from src.core.errors import UnauthorizedError


class TokenType(str, PyEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    sub: str
    type: TokenType
    jti: str
    exp: datetime
    iat: datetime


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    settings: Settings,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type.value,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(student_id: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return _create_token(
        student_id,
        TokenType.ACCESS,
        timedelta(minutes=settings.access_token_expire_minutes),
        settings,
    )


def create_refresh_token(student_id: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return _create_token(
        student_id,
        TokenType.REFRESH,
        timedelta(days=settings.refresh_token_expire_days),
        settings,
    )


def decode_token(token: str, expected_type: TokenType, settings: Settings | None = None) -> TokenPayload:
    settings = settings or get_settings()
    try:
        raw: dict[str, Any] = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid token") from exc

    payload = TokenPayload.model_validate(raw)
    if payload.type != expected_type:
        raise UnauthorizedError(f"Expected a {expected_type.value} token")
    return payload


SettingsDep = Annotated[Settings, Depends(get_settings)]
