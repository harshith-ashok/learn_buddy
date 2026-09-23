"""Seed load-test fixture data directly in Postgres and mint tokens for it.

Bypasses the HTTP API for setup (register/login/upload/wait-for-ingestion)
so the k6 run measures only the endpoints under test, not setup cost or
bcrypt/LLM latency. Requires DATABASE_URL to point at the target backend's
database — run from `backend/` with the same `.env` the backend itself
uses (see `backend/load-tests/README.md`).
"""

import asyncio
import json
import random
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.config import get_settings
from src.core.security import create_access_token, hash_password
from src.db.models import Document, DocumentStatus, MasteryScore, Student, Topic

_STUDENT_COUNT = 50
_OUTPUT_PATH = Path(__file__).parent / "seed-data.json"


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    users: list[dict[str, str]] = []

    async with session_factory() as db:
        for i in range(_STUDENT_COUNT):
            student = Student(
                email=f"load-test-{uuid.uuid4().hex[:8]}@example.com",
                hashed_password=hash_password("load-test-password"),
                full_name=f"Load Test {i}",
            )
            db.add(student)
            await db.flush()

            document = Document(
                student_id=student.id,
                filename="load-test.pdf",
                storage_path="/tmp/load-test.pdf",
                content_hash=uuid.uuid4().hex,
                status=DocumentStatus.DONE,
            )
            db.add(document)
            await db.flush()

            topic = Topic(
                document_id=document.id,
                name=f"Load Test Topic {i}",
                description="A topic seeded for load testing, with no ingested chunks behind it.",
                position=0,
            )
            db.add(topic)
            await db.flush()

            # Half start with some mastery (exercises the "has a
            # recommendation" path), half with none (exercises the
            # "everything mastered" / first-topic path) — a more
            # representative mix than every user looking identical.
            if random.random() < 0.5:
                db.add(MasteryScore(student_id=student.id, topic_id=topic.id, score=random.uniform(0.1, 0.6)))

            users.append({"access_token": create_access_token(str(student.id)), "topic_id": str(topic.id)})

        await db.commit()

    await engine.dispose()

    _OUTPUT_PATH.write_text(json.dumps(users, indent=2))
    print(f"Seeded {len(users)} load-test students -> {_OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
