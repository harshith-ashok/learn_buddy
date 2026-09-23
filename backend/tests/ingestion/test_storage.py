from pathlib import Path

from src.core.config import Settings
from src.ingestion.storage import compute_content_hash, read_file, save_file, storage_path


def test_content_hash_is_stable_and_content_sensitive() -> None:
    a = compute_content_hash(b"hello")
    b = compute_content_hash(b"hello")
    c = compute_content_hash(b"hello!")
    assert a == b
    assert a != c


def test_storage_path_is_keyed_by_student_and_hash(tmp_path: Path) -> None:
    settings = Settings(storage_dir=str(tmp_path))
    path = storage_path("student-1", "abc123", ".pdf", settings)
    assert path == tmp_path / "student-1" / "abc123.pdf"


async def test_save_and_read_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "file.docx"
    await save_file(b"binary content", path)

    assert await read_file(path) == b"binary content"


async def test_save_file_overwrites_on_identical_path(tmp_path: Path) -> None:
    path = tmp_path / "file.pdf"
    await save_file(b"first", path)
    await save_file(b"second", path)

    assert await read_file(path) == b"second"
