from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from src.core.cache import CacheClient, get_cache_client
from src.core.errors import RateLimitedError, UnauthorizedError
from src.core.llm_client import LLMClient, get_llm_client
from src.core.security import TokenType, decode_token
from src.core.vectorstore import VectorStoreClient, get_vectorstore_client
from src.db.models import Student
from src.db.session import DbSession

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_student(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> Student:
    """Resolve the bearer access token to its owning `Student`.

    Every protected route depends on this rather than trusting a raw
    student id from the request, so query scoping is enforced at the
    dependency level, not left to each handler.
    """
    if credentials is None:
        raise UnauthorizedError("Missing bearer token")

    payload = decode_token(credentials.credentials, TokenType.ACCESS)

    student = await db.scalar(select(Student).where(Student.id == payload.sub))
    if student is None:
        raise UnauthorizedError("Student not found")
    return student


CurrentStudent = Annotated[Student, Depends(get_current_student)]
LLMClientDep = Annotated[LLMClient, Depends(get_llm_client)]
VectorStoreDep = Annotated[VectorStoreClient, Depends(get_vectorstore_client)]
CacheDep = Annotated[CacheClient, Depends(get_cache_client)]


def rate_limiter(scope: str, limit: int, window_seconds: int) -> Callable[..., Awaitable[None]]:
    """FastAPI dependency factory: caps `scope` to `limit` requests per student per `window_seconds`.

    Fixed-window counting via `CacheClient.incr_with_ttl` — good enough for
    capping generation-endpoint cost, not a precise sliding-window limiter.
    """

    async def _enforce(student: CurrentStudent, cache: CacheDep) -> None:
        key = CacheClient.rate_limit_key(scope, str(student.id))
        count = await cache.incr_with_ttl(key, window_seconds)
        if count > limit:
            raise RateLimitedError(f"Too many {scope.replace('_', ' ')} requests — try again later")

    return _enforce
