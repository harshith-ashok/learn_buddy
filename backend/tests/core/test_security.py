import time

import pytest

from src.core.config import Settings
from src.core.errors import UnauthorizedError
from src.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(jwt_secret="test-secret", access_token_expire_minutes=1, refresh_token_expire_days=1)


def test_hash_password_roundtrip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_access_token_decodes_to_same_subject(settings: Settings) -> None:
    token = create_access_token("student-123", settings)
    payload = decode_token(token, TokenType.ACCESS, settings)
    assert payload.sub == "student-123"
    assert payload.type == TokenType.ACCESS


def test_refresh_token_rejected_as_access_token(settings: Settings) -> None:
    token = create_refresh_token("student-123", settings)
    with pytest.raises(UnauthorizedError):
        decode_token(token, TokenType.ACCESS, settings)


def test_expired_token_rejected(settings: Settings) -> None:
    expired_settings = settings.model_copy(update={"access_token_expire_minutes": 0})
    token = create_access_token("student-123", expired_settings)
    time.sleep(1)
    with pytest.raises(UnauthorizedError):
        decode_token(token, TokenType.ACCESS, expired_settings)


def test_tampered_token_rejected(settings: Settings) -> None:
    token = create_access_token("student-123", settings)
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    with pytest.raises(UnauthorizedError):
        decode_token(tampered, TokenType.ACCESS, settings)
