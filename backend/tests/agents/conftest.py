import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.db.models import Document, DocumentStatus, MasteryScore, Student, Topic, TopicPrerequisite

# `fake_agent_llm` lives in the root tests/conftest.py — shared with tests/api/.


@pytest_asyncio.fixture
async def student(db_session: AsyncSession) -> Student:
    new_student = Student(
        email=f"{uuid.uuid4().hex}@example.com", hashed_password=hash_password("x"), full_name="Student"
    )
    db_session.add(new_student)
    await db_session.flush()
    return new_student


@pytest_asyncio.fixture
async def make_document(db_session: AsyncSession, student: Student):
    async def _make(exam_date=None) -> Document:
        document = Document(
            student_id=student.id,
            filename="notes.pdf",
            storage_path="/tmp/notes.pdf",
            content_hash=uuid.uuid4().hex,
            status=DocumentStatus.DONE,
            exam_date=exam_date,
        )
        db_session.add(document)
        await db_session.flush()
        return document

    return _make


@pytest_asyncio.fixture
async def make_topic(db_session: AsyncSession):
    async def _make(document: Document, name: str, description: str = "", position: int = 0) -> Topic:
        topic = Topic(document_id=document.id, name=name, description=description, position=position)
        db_session.add(topic)
        await db_session.flush()
        return topic

    return _make


@pytest_asyncio.fixture
async def set_mastery(db_session: AsyncSession, student: Student):
    async def _set(topic: Topic, score: float, consecutive_failures: int = 0) -> MasteryScore:
        mastery = MasteryScore(
            student_id=student.id, topic_id=topic.id, score=score, consecutive_failures=consecutive_failures
        )
        db_session.add(mastery)
        await db_session.flush()
        return mastery

    return _set


@pytest_asyncio.fixture
async def add_prerequisite(db_session: AsyncSession):
    async def _add(topic: Topic, prerequisite: Topic) -> TopicPrerequisite:
        edge = TopicPrerequisite(topic_id=topic.id, prerequisite_topic_id=prerequisite.id)
        db_session.add(edge)
        await db_session.flush()
        return edge

    return _add
