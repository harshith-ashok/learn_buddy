from src.core.config import Settings, get_settings
from src.ingestion.schemas import Chunk, ParsedDocument, ParsedSection


def _split_words(text: str, target_tokens: int, overlap_tokens: int) -> list[str]:
    """Split `text` into ~`target_tokens`-word chunks with `overlap_tokens` of overlap.

    Word count is used as a token-count proxy: it's model-agnostic (no
    tokenizer dependency tied to a specific encoding) and close enough for
    a target chunk *size*, which only needs to be roughly consistent, not
    exact.
    """
    words = text.split()
    if not words:
        return []

    stride = max(target_tokens - overlap_tokens, 1)
    chunks: list[str] = []
    start = 0
    while start < len(words):
        window = words[start : start + target_tokens]
        chunks.append(" ".join(window))
        if start + target_tokens >= len(words):
            break
        start += stride
    return chunks


def _walk(section: ParsedSection) -> list[tuple[str | None, str]]:
    """DFS over the section tree, pairing each node's own text with its heading."""
    pairs: list[tuple[str | None, str]] = []
    if section.text.strip():
        pairs.append((section.heading, section.text))
    for child in section.children:
        pairs.extend(_walk(child))
    return pairs


def chunk_document(document: ParsedDocument, settings: Settings | None = None) -> list[Chunk]:
    """Chunk every section's text by heading structure, in document order.

    Each section is chunked independently of its siblings/children, so a
    chunk never straddles a heading boundary; long sections still split
    into multiple ~`chunk_target_tokens`-word chunks with
    `chunk_overlap_tokens` of overlap between consecutive chunks.
    """
    settings = settings or get_settings()
    chunks: list[Chunk] = []
    order = 0

    for section in document.sections:
        for heading, text in _walk(section):
            for piece in _split_words(text, settings.chunk_target_tokens, settings.chunk_overlap_tokens):
                chunks.append(
                    Chunk(
                        order=order,
                        section_heading=heading,
                        text=piece,
                        token_count=len(piece.split()),
                    )
                )
                order += 1

    return chunks
