import asyncio
import hashlib
from pathlib import Path

from src.core.config import Settings, get_settings


def compute_content_hash(content: bytes) -> str:
    """SHA-256 of the raw file bytes — the basis for upload idempotency."""
    return hashlib.sha256(content).hexdigest()


def storage_path(
    student_id: str, content_hash: str, extension: str, settings: Settings | None = None
) -> Path:
    """Where a document's raw bytes live on disk.

    Keyed by `(student_id, content_hash)` rather than a generated id: an
    identical re-upload resolves to the same path, so writing it is a
    no-op overwrite instead of a second copy.
    """
    settings = settings or get_settings()
    return Path(settings.storage_dir) / student_id / f"{content_hash}{extension}"


async def save_file(content: bytes, path: Path) -> None:
    def _write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    await asyncio.to_thread(_write)


async def read_file(path: Path) -> bytes:
    return await asyncio.to_thread(path.read_bytes)
