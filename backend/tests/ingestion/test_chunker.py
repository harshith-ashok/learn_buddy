from src.core.config import Settings
from src.ingestion.chunker import chunk_document
from src.ingestion.schemas import ParsedDocument, ParsedSection


def _settings(target: int = 10, overlap: int = 2) -> Settings:
    return Settings(chunk_target_tokens=target, chunk_overlap_tokens=overlap)


def _words(n: int, prefix: str = "word") -> str:
    return " ".join(f"{prefix}{i}" for i in range(n))


def test_no_headings_single_flat_section_still_chunks() -> None:
    document = ParsedDocument(
        title=None,
        sections=[ParsedSection(heading=None, level=0, text=_words(35), children=[])],
    )

    chunks = chunk_document(document, _settings(target=10, overlap=2))

    assert len(chunks) > 1
    assert all(chunk.section_heading is None for chunk in chunks)
    assert [chunk.order for chunk in chunks] == list(range(len(chunks)))


def test_very_short_document_produces_one_chunk() -> None:
    document = ParsedDocument(
        title="Tiny",
        sections=[ParsedSection(heading="Intro", level=1, text="Just a few words here.", children=[])],
    )

    chunks = chunk_document(document, _settings(target=400, overlap=50))

    assert len(chunks) == 1
    assert chunks[0].section_heading == "Intro"
    assert chunks[0].text == "Just a few words here."


def test_table_like_text_chunks_without_crashing() -> None:
    rows = "\n".join(f"row{i}col1 | row{i}col2 | row{i}col3" for i in range(20))
    document = ParsedDocument(
        title=None,
        sections=[ParsedSection(heading="Pricing Table", level=1, text=rows, children=[])],
    )

    chunks = chunk_document(document, _settings(target=10, overlap=2))

    assert len(chunks) > 1
    assert all(chunk.section_heading == "Pricing Table" for chunk in chunks)
    # every word from the source survives somewhere in the chunked output
    original_words = set(rows.split())
    chunked_words = {w for chunk in chunks for w in chunk.text.split()}
    assert original_words <= chunked_words


def test_empty_section_text_produces_no_chunks() -> None:
    document = ParsedDocument(
        title=None,
        sections=[ParsedSection(heading="Empty", level=1, text="   ", children=[])],
    )

    assert chunk_document(document, _settings()) == []


def test_nested_sections_chunk_independently_in_document_order() -> None:
    document = ParsedDocument(
        title="Course",
        sections=[
            ParsedSection(
                heading="Chapter 1",
                level=1,
                text=_words(5, "ch1"),
                children=[
                    ParsedSection(heading="1.1 Basics", level=2, text=_words(5, "s11"), children=[]),
                ],
            ),
            ParsedSection(heading="Chapter 2", level=1, text=_words(5, "ch2"), children=[]),
        ],
    )

    chunks = chunk_document(document, _settings(target=400, overlap=50))

    assert [c.section_heading for c in chunks] == ["Chapter 1", "1.1 Basics", "Chapter 2"]
    assert [c.order for c in chunks] == [0, 1, 2]


def test_consecutive_chunks_overlap() -> None:
    document = ParsedDocument(
        title=None,
        sections=[ParsedSection(heading=None, level=0, text=_words(24), children=[])],
    )

    chunks = chunk_document(document, _settings(target=10, overlap=3))

    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert first_words[-3:] == second_words[:3]
